#!/usr/bin/env python3
"""
Local smoke test for Matrixly Voice Receptionist (Grok Voice / xAI Realtime).

Connects with a pre-built Voice Agent Builder agent_id, sends a text turn,
prints the assistant transcript, and optionally writes raw PCM16 audio.

Requires:
  XAI_API_KEY in the environment (or agents/voice-receptionist/.env)

Usage (from repo root or this package):
  cd agents/voice-receptionist
  python -m venv .venv
  .\\.venv\\Scripts\\Activate.ps1   # Windows
  pip install -r requirements.txt
  copy .env.example .env           # then set XAI_API_KEY
  python scripts/smoke_test.py

Exit 0 on success (transcript received). Exit 1 on config/API failure.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("Missing dependency: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)

DEFAULT_AGENT_ID = "agent_1O5oHoZt3hfnOBtI"
DEFAULT_PROMPT = "Hello! What does Matrixly do for small businesses?"
WS_URL_TMPL = "wss://api.x.ai/v1/realtime?agent_id={agent_id}"
# Default Grok Voice output is PCM16 LE mono @ 24 kHz when using JSON deltas
DEFAULT_PCM_RATE = 24000


def _load_env() -> None:
    if load_dotenv is None:
        return
    # package .env, then cwd
    load_dotenv(ROOT / ".env")
    load_dotenv()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Matrixly Grok Voice local smoke test")
    p.add_argument(
        "--agent-id",
        default=os.environ.get("MATRIXLY_VOICE_AGENT_ID", DEFAULT_AGENT_ID),
        help="Voice Agent Builder agent_id",
    )
    p.add_argument(
        "--prompt",
        default=os.environ.get("VOICE_SMOKE_PROMPT", DEFAULT_PROMPT),
        help="User text turn to send",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("VOICE_SMOKE_TIMEOUT", "60")),
        help="Max seconds to wait for response.done",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "smoke",
        help="Directory for PCM / transcript artifacts",
    )
    p.add_argument(
        "--no-audio-file",
        action="store_true",
        help="Do not write PCM file (still decode deltas for size check)",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print all realtime event types",
    )
    return p.parse_args()


async def run_smoke(
    *,
    api_key: str,
    agent_id: str,
    prompt: str,
    timeout: float,
    out_dir: Path,
    write_audio: bool,
    verbose: bool,
) -> dict:
    url = WS_URL_TMPL.format(agent_id=agent_id)
    headers = {"Authorization": f"Bearer {api_key}"}

    transcript_parts: list[str] = []
    pcm_chunks: list[bytes] = []
    events_seen: list[str] = []
    errors: list[dict] = []
    tool_calls: list[dict] = []
    response_done = False
    started = time.monotonic()

    async with websockets.connect(
        url,
        additional_headers=headers,
        open_timeout=30,
        close_timeout=10,
        max_size=16 * 1024 * 1024,
    ) as ws:
        # Text turn (smoke only — phone path would stream input audio instead)
        await ws.send(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    },
                }
            )
        )
        await ws.send(json.dumps({"type": "response.create"}))

        while True:
            if time.monotonic() - started > timeout:
                raise TimeoutError(f"No response.done within {timeout}s")

            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(15.0, timeout))
            except asyncio.TimeoutError:
                if response_done:
                    break
                continue
            except ConnectionClosed as e:
                if response_done:
                    break
                raise RuntimeError(f"WebSocket closed early: {e}") from e

            if isinstance(raw, bytes):
                # Binary audio transport (if enabled on session) — collect as-is
                pcm_chunks.append(raw)
                if verbose:
                    print(f"[binary] {len(raw)} bytes", file=sys.stderr)
                continue

            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                if verbose:
                    print(f"[non-json] {raw[:80]!r}", file=sys.stderr)
                continue

            etype = event.get("type") or "unknown"
            events_seen.append(etype)
            if verbose:
                print(f"[event] {etype}", file=sys.stderr)

            if etype == "error":
                errors.append(event)
                break

            # Transcript streaming (Builder / Realtime naming variants)
            if etype in (
                "response.output_audio_transcript.delta",
                "response.audio_transcript.delta",
            ):
                delta = event.get("delta") or ""
                if delta:
                    transcript_parts.append(delta)
                    print(delta, end="", flush=True)

            elif etype in (
                "response.output_audio.delta",
                "response.audio.delta",
            ):
                b64 = event.get("delta") or ""
                if b64:
                    pcm_chunks.append(base64.b64decode(b64))

            elif etype == "response.function_call_arguments.done":
                tool_calls.append(
                    {
                        "name": event.get("name"),
                        "call_id": event.get("call_id"),
                        "arguments": event.get("arguments"),
                    }
                )
                print(
                    f"\n[tool] {event.get('name')} args={event.get('arguments')}",
                    flush=True,
                )

            elif etype == "response.done":
                response_done = True
                print(flush=True)
                break

    transcript = "".join(transcript_parts).strip()
    pcm_bytes = b"".join(pcm_chunks)
    out_dir.mkdir(parents=True, exist_ok=True)

    pcm_path = None
    if write_audio and pcm_bytes:
        pcm_path = out_dir / "smoke_reply.pcm"
        pcm_path.write_bytes(pcm_bytes)

    transcript_path = out_dir / "smoke_transcript.txt"
    transcript_path.write_text(transcript or "(empty)", encoding="utf-8")

    return {
        "agent_id": agent_id,
        "prompt": prompt,
        "transcript": transcript,
        "transcript_chars": len(transcript),
        "pcm_bytes": len(pcm_bytes),
        "pcm_path": str(pcm_path) if pcm_path else None,
        "transcript_path": str(transcript_path),
        "pcm_rate_hz": DEFAULT_PCM_RATE,
        "tool_calls": tool_calls,
        "errors": errors,
        "events": events_seen,
        "elapsed_s": round(time.monotonic() - started, 2),
        "response_done": response_done,
    }


def main() -> int:
    _load_env()
    args = _parse_args()
    api_key = (os.environ.get("XAI_API_KEY") or "").strip()
    if not api_key:
        print(
            "XAI_API_KEY is not set.\n"
            "  1. copy agents/voice-receptionist/.env.example → .env\n"
            "  2. paste your key from https://console.x.ai/\n"
            "  3. re-run: python scripts/smoke_test.py",
            file=sys.stderr,
        )
        return 1

    print(f"Connecting agent_id={args.agent_id} …", flush=True)
    print(f"Prompt: {args.prompt!r}", flush=True)
    print("--- assistant ---", flush=True)

    try:
        result = asyncio.run(
            run_smoke(
                api_key=api_key,
                agent_id=args.agent_id,
                prompt=args.prompt,
                timeout=args.timeout,
                out_dir=args.out_dir,
                write_audio=not args.no_audio_file,
                verbose=args.verbose,
            )
        )
    except Exception as e:
        print(f"\nSMOKE FAIL: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if result["errors"]:
        print("SMOKE FAIL: API error event(s)", result["errors"], file=sys.stderr)
        return 1

    if not result["response_done"]:
        print("SMOKE FAIL: response.done never received", file=sys.stderr)
        return 1

    # Success if we got transcript and/or audio (some agents may be audio-only)
    if result["transcript_chars"] == 0 and result["pcm_bytes"] == 0:
        print(
            "SMOKE FAIL: empty transcript and no audio deltas "
            f"(events={result['events'][-12:]})",
            file=sys.stderr,
        )
        return 1

    print("--- summary ---")
    print(
        "SMOKE OK",
        {
            "agent_id": result["agent_id"],
            "transcript_chars": result["transcript_chars"],
            "pcm_bytes": result["pcm_bytes"],
            "tool_calls": len(result["tool_calls"]),
            "elapsed_s": result["elapsed_s"],
            "transcript_path": result["transcript_path"],
            "pcm_path": result["pcm_path"],
        },
    )
    if result["pcm_path"]:
        print(
            f"Play PCM (24 kHz mono s16le):\n"
            f"  ffplay -f s16le -ar {DEFAULT_PCM_RATE} -ac 1 {result['pcm_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

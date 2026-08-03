# Matrixly Voice Receptionist

**Marketplace tile (planned):** VOICE · **Domain:** Inbound calls / front desk  
**Stack:** [Grok Voice](https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech) (xAI Realtime WebSocket) + pre-built **Voice Agent Builder** `agent_id`.

This package starts as a **local smoke test** that proves your xAI key + Builder agent respond with transcript (and optional PCM audio). Telephony (Twilio / SIP inbound) comes next.

---

## Prerequisites

1. An [xAI API key](https://console.x.ai/)
2. A Voice Agent created in the [Grok Voice Agent Builder](https://x.ai/api/voice) (or use the sample `agent_id` from your console export)
3. Python 3.11+ recommended

---

## Local smoke test

```powershell
cd agents/voice-receptionist
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env → set XAI_API_KEY=...
python scripts/smoke_test.py
```

### What success looks like

- Assistant text streams to the terminal
- Exit code `0` and a line starting with `SMOKE OK`
- Artifacts under `data/smoke/`:
  - `smoke_transcript.txt`
  - `smoke_reply.pcm` (raw PCM16 LE mono @ 24 kHz)

Play the PCM (if `ffmpeg` / `ffplay` is installed):

```powershell
ffplay -f s16le -ar 24000 -ac 1 data/smoke/smoke_reply.pcm
```

### Options

```powershell
python scripts/smoke_test.py --prompt "How much is Grow pricing?"
python scripts/smoke_test.py --agent-id agent_xxxx -v
python scripts/smoke_test.py --timeout 90 --no-audio-file
```

| Env var | Purpose |
|---------|---------|
| `XAI_API_KEY` | Required |
| `MATRIXLY_VOICE_AGENT_ID` | Builder agent id (default: sample id in script) |
| `VOICE_SMOKE_PROMPT` | Default user text turn |
| `VOICE_SMOKE_TIMEOUT` | Seconds to wait for `response.done` |

---

## How the smoke test works

```
Python client
    │  Authorization: Bearer XAI_API_KEY
    ▼
wss://api.x.ai/v1/realtime?agent_id=...
    │  conversation.item.create (input_text)
    │  response.create
    ▼
Builder agent (persona / tools / knowledge from xAI console)
    │  response.output_audio_transcript.delta
    │  response.output_audio.delta  → base64 PCM
    ▼
Terminal + data/smoke/*
```

This is a **text-in** probe of the agent session. Real phone calls will instead:

1. Receive `realtime.call.incoming` webhook with `call_id`
2. Join `wss://api.x.ai/v1/realtime?call_id=...`
3. Stream caller audio (G.711 / PCM) with server VAD

---

## Next (not in this smoke package yet)

- [ ] FastAPI webhook for SIP / Twilio inbound
- [ ] Tool handlers → BookWise / SupportForge / lead capture
- [ ] Human transfer (`refer`) + call hangup
- [ ] Marketplace listing + agent product page

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `XAI_API_KEY is not set` | `.env` in this folder; restart shell after edit |
| Auth / 401 style disconnect | Key valid and has Voice API access |
| Empty transcript & no audio | Wrong `agent_id`, or agent disabled in Builder |
| Timeout | Raise `--timeout 90`; check network / firewall on WSS |
| Tool printed but no final reply | Smoke does not execute tools yet — configure Builder tools as server-side or add handlers later |

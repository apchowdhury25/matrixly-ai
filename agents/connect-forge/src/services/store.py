"""JSON persistence for messages, conversations, calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import CallRecord, ConversationThread, SmsMessage, utc_now


class MessageStore:
    def __init__(self, data_dir: str | Path) -> None:
        data_dir = Path(data_dir)
        self.msg_dir = data_dir / "messages"
        self.conv_dir = data_dir / "conversations"
        self.call_dir = data_dir / "calls"
        for d in (self.msg_dir, self.conv_dir, self.call_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_message(self, msg: SmsMessage) -> SmsMessage:
        path = self.msg_dir / f"{msg.id}.json"
        path.write_text(json.dumps(msg.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return msg

    def get_message(self, msg_id: str) -> SmsMessage | None:
        path = self.msg_dir / f"{msg_id}.json"
        if not path.exists():
            return None
        return SmsMessage(**json.loads(path.read_text(encoding="utf-8")))

    def list_messages(self, limit: int = 50) -> list[SmsMessage]:
        items: list[SmsMessage] = []
        for p in sorted(self.msg_dir.glob("*.json"), reverse=True):
            try:
                items.append(SmsMessage(**json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
            if len(items) >= limit:
                break
        return items

    def save_conversation(self, conv: ConversationThread) -> ConversationThread:
        conv.updated_at = utc_now()
        path = self.conv_dir / f"{conv.id}.json"
        path.write_text(
            json.dumps(conv.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return conv

    def get_conversation(self, conv_id: str) -> ConversationThread | None:
        path = self.conv_dir / f"{conv_id}.json"
        if not path.exists():
            return None
        return ConversationThread(**json.loads(path.read_text(encoding="utf-8")))

    def find_conversation_by_number(self, number: str) -> ConversationThread | None:
        num = number.strip()
        for c in self.list_conversations(limit=200):
            if c.participant_number == num:
                return c
        return None

    def list_conversations(self, limit: int = 50) -> list[ConversationThread]:
        items: list[ConversationThread] = []
        for p in sorted(self.conv_dir.glob("*.json"), reverse=True):
            try:
                items.append(ConversationThread(**json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
            if len(items) >= limit:
                break
        return items

    def save_call(self, call: CallRecord) -> CallRecord:
        path = self.call_dir / f"{call.id}.json"
        path.write_text(json.dumps(call.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        return call

    def list_calls(self, limit: int = 30) -> list[CallRecord]:
        items: list[CallRecord] = []
        for p in sorted(self.call_dir.glob("*.json"), reverse=True):
            try:
                items.append(CallRecord(**json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
            if len(items) >= limit:
                break
        return items

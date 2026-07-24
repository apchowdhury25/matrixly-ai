"""Template management — load, list, upload approved markdown templates."""

from __future__ import annotations

import re
from pathlib import Path


class TemplateStore:
    def __init__(self, templates_dir: str | Path) -> None:
        self.dir = Path(templates_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict]:
        items = []
        for p in sorted(self.dir.glob("*.md")):
            items.append(
                {
                    "id": p.stem,
                    "name": p.stem.replace("-", " ").replace("_", " ").title(),
                    "path": str(p),
                    "bytes": p.stat().st_size,
                }
            )
        return items

    def get(self, template_id: str) -> str:
        # sanitize
        safe = re.sub(r"[^a-zA-Z0-9_-]", "", template_id or "")
        path = self.dir / f"{safe}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        # fallback proposal
        fallback = self.dir / "proposal.md"
        if fallback.exists():
            return fallback.read_text(encoding="utf-8")
        return "# {{title}}\n\n{{summary}}\n\n{{pricing_table}}\n\n{{legal_block}}\n"

    def save(self, template_id: str, content: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "", template_id or "custom")
        if not safe:
            safe = "custom"
        path = self.dir / f"{safe}.md"
        path.write_text(content, encoding="utf-8")
        return path

    def render(self, template_id: str, values: dict[str, str]) -> str:
        text = self.get(template_id)
        for k, v in values.items():
            text = text.replace("{{" + k + "}}", str(v if v is not None else ""))
        # clear any leftover simple tokens
        text = re.sub(r"\{\{[a-zA-Z0-9_]+\}\}", "", text)
        return text

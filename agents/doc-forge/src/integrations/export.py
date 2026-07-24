"""Export documents to MD, HTML, TXT, and simple PDF."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from ..models import Document, utc_now


class DocumentExporter:
    def __init__(self, data_dir: str | Path, cfg: dict) -> None:
        self.cfg = cfg
        self.dir = Path(data_dir) / "exports"
        self.dir.mkdir(parents=True, exist_ok=True)

    def export(self, doc: Document, formats: list[str] | None = None) -> list[str]:
        allowed = (self.cfg.get("documents") or {}).get("export_formats") or [
            "md",
            "html",
            "pdf",
            "txt",
        ]
        formats = formats or list(allowed)
        base = self.dir / doc.id / f"v{doc.version}"
        base.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []

        md = doc.body_markdown or ""
        if "md" in formats:
            p = base / f"{doc.id}.md"
            p.write_text(md, encoding="utf-8")
            paths.append(str(p))
        if "txt" in formats:
            p = base / f"{doc.id}.txt"
            p.write_text(_md_to_text(md), encoding="utf-8")
            paths.append(str(p))
        if "html" in formats:
            p = base / f"{doc.id}.html"
            p.write_text(_md_to_html(doc, md, self.cfg), encoding="utf-8")
            paths.append(str(p))
        if "pdf" in formats:
            p = base / f"{doc.id}.pdf"
            write_simple_pdf(p, doc.title or doc.id, _md_to_text(md))
            paths.append(str(p))

        meta = base / "meta.json"
        meta.write_text(
            json.dumps(
                {
                    "document_id": doc.id,
                    "version": doc.version,
                    "status": doc.status.value,
                    "exported_at": utc_now(),
                    "formats": formats,
                    "paths": paths,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        paths.append(str(meta))
        doc.export_paths = paths
        return paths


def _md_to_text(md: str) -> str:
    text = md
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\|", " ", text)
    return text


def _md_to_html(doc: Document, md: str, cfg: dict) -> str:
    brand = cfg.get("brand") or {}
    color = brand.get("primary_color") or "#117ACA"
    lines = []
    for line in md.splitlines():
        if line.startswith("# "):
            lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            lines.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("|"):
            lines.append(f"<pre class='table'>{html.escape(line)}</pre>")
        elif line.strip() == "---":
            lines.append("<hr/>")
        elif line.startswith("- "):
            lines.append(f"<li>{html.escape(line[2:])}</li>")
        elif not line.strip():
            lines.append("<br/>")
        else:
            safe = html.escape(line)
            safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
            lines.append(f"<p>{safe}</p>")
    body = "\n".join(lines)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>{html.escape(doc.title or doc.id)}</title>
<style>
  body {{ font-family: 'Segoe UI', Open Sans, Arial, sans-serif; max-width: 800px; margin: 2rem auto; color: #211E1E; line-height: 1.55; }}
  h1,h2,h3 {{ color: {color}; }}
  hr {{ border: none; border-top: 1px solid #D0D7DE; margin: 1.5rem 0; }}
  pre.table {{ font-size: 0.85rem; background: #F0F4F8; padding: 0.25rem 0.5rem; }}
  .meta {{ color: #5C6670; font-size: 0.9rem; margin-bottom: 1.5rem; }}
</style></head>
<body>
<div class="meta">Document {html.escape(doc.id)} · v{doc.version} · {html.escape(doc.status.value)}</div>
{body}
</body></html>
"""


def write_simple_pdf(path: Path, title: str, text: str) -> None:
    """Minimal multi-page text PDF (no third-party deps)."""

    def pdf_escape(s: str) -> str:
        return (
            s.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("\r", "")
        )

    wrapped: list[str] = [title[:80], ""]
    for para in text.splitlines():
        para = para.strip()
        if not para:
            wrapped.append("")
            continue
        while len(para) > 95:
            wrapped.append(para[:95])
            para = para[95:]
        wrapped.append(para)

    pages: list[list[str]] = []
    cur: list[str] = []
    for line in wrapped:
        cur.append(line)
        if len(cur) >= 58:
            pages.append(cur)
            cur = []
    if cur:
        pages.append(cur)
    if not pages:
        pages = [[title[:80]]]

    objects: list[bytes] = []

    def add(payload: bytes) -> int:
        objects.append(payload)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    content_ids: list[int] = []
    for plines in pages:
        cmds = ["BT", "/F1 10 Tf", "50 800 Td", "12 TL"]
        first = True
        for line in plines:
            cl = pdf_escape(line)[:110]
            if first:
                cmds.append(f"({cl}) Tj")
                first = False
            else:
                cmds.append("T*")
                cmds.append(f"({cl}) Tj")
        cmds.append("ET")
        stream = "\n".join(cmds).encode("latin-1", errors="replace")
        content_ids.append(
            add(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")
        )

    # Page objects will reference pages tree; number = current_len + index + 1, pages after all pages
    page_start = len(objects) + 1
    pages_id = page_start + len(content_ids)
    page_ids: list[int] = []
    for c_id in content_ids:
        pid = add(
            (
                f"<< /Type /Page /Parent {pages_id} 0 R "
                f"/MediaBox [0 0 612 792] "
                f"/Contents {c_id} 0 R "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
            ).encode("ascii")
        )
        page_ids.append(pid)

    kids = " ".join(f"{n} 0 R" for n in page_ids)
    # pages_id should equal len(objects)+1 now
    actual_pages_id = add(
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    )
    catalog_id = add(f"<< /Type /Catalog /Pages {actual_pages_id} 0 R >>".encode("ascii"))

    # If pages_id prediction mismatched, fix page Parent refs
    if actual_pages_id != pages_id:
        fixed: list[bytes] = []
        for i, obj in enumerate(objects, start=1):
            if i in page_ids:
                fixed.append(
                    obj.replace(
                        f"/Parent {pages_id} 0 R".encode("ascii"),
                        f"/Parent {actual_pages_id} 0 R".encode("ascii"),
                    )
                )
            else:
                fixed.append(obj)
        objects = fixed

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(bytes(out))

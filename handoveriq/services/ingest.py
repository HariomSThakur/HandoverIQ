from __future__ import annotations

import hashlib
import re
from pathlib import PurePath

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Chunk, Source

MAX_UPLOAD_BYTES = 1024 * 1024
ACCESS_LEVELS = ("public", "team", "restricted")
ACCESS_RANK = {level: rank for rank, level in enumerate(ACCESS_LEVELS)}


class IngestError(ValueError):
    pass


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_for_match(value: str) -> str:
    """Collapse whitespace only; keep case and punctuation significant."""
    return re.sub(r"\s+", " ", value).strip()


def quote_is_present(source_text: str, quote: str) -> bool:
    normalized_quote = normalize_for_match(quote)
    return bool(normalized_quote) and normalized_quote in normalize_for_match(source_text)


def split_chunks(source_id: str, content: str, max_chars: int = 1600) -> list[Chunk]:
    spans: list[tuple[int, int]] = []
    for paragraph_match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\Z)", content, re.S):
        start, end = paragraph_match.span()
        while end - start > max_chars:
            cutoff = content.rfind(" ", start, start + max_chars)
            if cutoff <= start:
                cutoff = start + max_chars
            spans.append((start, cutoff))
            start = cutoff
            while start < end and content[start].isspace():
                start += 1
        if start < end:
            spans.append((start, end))

    chunks: list[Chunk] = []
    for ordinal, (start, end) in enumerate(spans):
        text = content[start:end]
        chunk_id = _sha256(f"{source_id}:{start}:{end}:{text}".encode("utf-8"))
        chunks.append(Chunk(
            chunk_id=chunk_id,
            source_id=source_id,
            ordinal=ordinal,
            start_offset=start,
            end_offset=end,
            content=text,
        ))
    return chunks


def validate_upload(filename: str, raw: bytes, access_level: str) -> tuple[str, str, str]:
    safe_name = PurePath(filename.replace("\\", "/")).name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise IngestError("Choose a file with a name.")
    if PurePath(safe_name).suffix.lower() not in {".md", ".txt"}:
        raise IngestError("Only Markdown (.md) and plain text (.txt) files are accepted.")
    if access_level not in ACCESS_LEVELS:
        raise IngestError("Choose a valid access label.")
    if not raw:
        raise IngestError("The file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise IngestError("Each file must be 1 MiB or smaller.")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestError("The file must use UTF-8 text encoding.") from exc
    if not content.strip():
        raise IngestError("The file contains no readable text.")
    source_id = _sha256((safe_name + "\0" + content).encode("utf-8"))
    return safe_name, content, source_id


def store_source(
    session: Session,
    filename: str,
    raw: bytes,
    access_level: str,
    source_type: str = "upload",
) -> tuple[Source, bool]:
    safe_name, content, source_id = validate_upload(filename, raw, access_level)
    existing = session.get(Source, source_id)
    if existing is not None:
        # Re-importing identical content cannot weaken its prior access label.
        if ACCESS_RANK[access_level] > ACCESS_RANK[existing.access_level]:
            existing.access_level = access_level
        return existing, False

    source = Source(
        source_id=source_id,
        filename=safe_name,
        access_level=access_level,
        source_type=source_type,
        content=content,
    )
    source.chunks = split_chunks(source_id, content)
    session.add(source)
    return source, True


def load_demo_sources(session: Session, demo_root) -> tuple[int, int]:
    import json
    from pathlib import Path

    root = Path(demo_root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    inserted = 0
    already_present = 0
    for entry in manifest["sources"]:
        path = root / entry["filename"]
        source, created = store_source(
            session=session,
            filename=path.name,
            raw=path.read_bytes(),
            access_level=entry["access_level"],
            source_type="demo",
        )
        inserted += int(created)
        already_present += int(not created)
    return inserted, already_present


def get_chunks(session: Session, source_id: str) -> list[Chunk]:
    return list(session.scalars(
        select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.ordinal)
    ))

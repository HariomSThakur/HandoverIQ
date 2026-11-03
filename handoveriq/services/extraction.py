from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Claim, Chunk, Source
from .ingest import quote_is_present

CLAIM_TYPES = {
    "decision", "owner", "open_action", "risk", "dependency", "date", "question", "context"
}


@dataclass
class ExtractionSummary:
    created: int = 0
    local: int = 0
    model: int = 0
    skipped_restricted: int = 0
    model_errors: int = 0
    model_error_message: str | None = None


def _kind_for(text: str) -> str:
    lowered = text.casefold()
    if "?" in text or any(word in lowered for word in ("unresolved", "open question", "not decided")):
        return "question"
    if any(word in lowered for word in ("risk", "blocked", "blocker", "may fail", "concern", "uncertain")):
        return "risk"
    if any(word in lowered for word in ("depends on", "dependency", "requires the", "requires a", "requires an")):
        return "dependency"
    if any(word in lowered for word in ("decided", "decision", "selected", "switched to", "we chose")):
        return "decision"
    if any(word in lowered for word in ("todo", "to do", "follow up", "needs to", "must ", "will ", "action:")):
        return "open_action"
    if re.search(r"\b(?:owner|owns|assigned to|responsible for)\b", lowered):
        return "owner"
    if re.search(r"\b(?:20\d{2}-\d{2}-\d{2}|jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b", lowered):
        return "date"
    return "context"


def _owner_for(text: str) -> str | None:
    patterns = (
        r"\bowner\s*[:=-]\s*([A-Z][\w-]*(?:\s+[A-Z][\w-]*)?)",
        r"\b([A-Z][\w-]*(?:\s+[A-Z][\w-]*)?)\s+(?:owns|will lead|is responsible for|handles)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return None


def _date_for(text: str) -> str | None:
    match = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text)
    return match.group(0) if match else None


def _sentences(content: str) -> list[str]:
    cleaned: list[str] = []
    for line in content.splitlines():
        value = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if not value or value.startswith("#") or value.startswith("|"):
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", value):
            sentence = sentence.strip()
            if len(sentence) >= 24:
                cleaned.append(sentence[:600])
    return cleaned


def deterministic_claims(chunks: list[Chunk]) -> list[dict]:
    result = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        for sentence in _sentences(chunk.content):
            key = (sentence.casefold(), chunk.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            result.append({
                "claim_text": sentence,
                "claim_type": _kind_for(sentence),
                "owner": _owner_for(sentence),
                "due_date": _date_for(sentence),
                "evidence_quote": sentence,
                "chunk_id": chunk.chunk_id,
            })
    return result


def _schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim_text": {"type": "string"},
                        "claim_type": {"type": "string", "enum": sorted(CLAIM_TYPES)},
                        "owner": {"type": ["string", "null"]},
                        "due_date": {"type": ["string", "null"]},
                        "evidence_quote": {"type": "string"},
                        "chunk_id": {"type": "string"},
                    },
                    "required": ["claim_text", "claim_type", "owner", "due_date", "evidence_quote", "chunk_id"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["claims"],
        "additionalProperties": False,
    }


def _response_output_text(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValueError("The model response was not an object.")
    texts = []
    output_items = data.get("output", [])
    if not isinstance(output_items, list):
        raise ValueError("The model response had an invalid output list.")
    for item in output_items:
        if not isinstance(item, dict):
            raise ValueError("The model response contained an invalid output item.")
        if item.get("type") != "message":
            continue
        content_items = item.get("content", [])
        if not isinstance(content_items, list):
            raise ValueError("The model response had invalid message content.")
        for content in content_items:
            if not isinstance(content, dict):
                raise ValueError("The model response contained an invalid content item.")
            if content.get("type") == "refusal":
                raise ValueError("The model refused to process this source.")
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise ValueError("The model response did not contain structured output.")
    return "\n".join(texts)


def _call_responses_api(chunks: list[Chunk], api_key: str, model: str, timeout: int = 30) -> list[dict]:
    chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
    chunk_payload = [{"chunk_id": chunk.chunk_id, "text": chunk.content} for chunk in chunks]
    request_data = {
        "model": model,
        "store": False,
        "input": [
            {
                "role": "system",
                "content": (
                    "Extract only concrete project facts stated in the supplied source chunks. "
                    "Do not infer. Each claim must cite a verbatim evidence_quote from exactly one "
                    "supplied chunk and use that chunk's chunk_id. Keep questions as questions. "
                    "Return no claim when there is no useful supported statement."
                ),
            },
            {"role": "user", "content": json.dumps(chunk_payload, ensure_ascii=False)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "handover_claims",
                "strict": True,
                "schema": _schema(),
            }
        },
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_data).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        raise RuntimeError(f"Model API returned HTTP {exc.code}: {detail[:400]}") from exc
    parsed = json.loads(_response_output_text(data))
    if not isinstance(parsed, dict):
        raise ValueError("The model output root was not an object.")
    claims = parsed.get("claims")
    if not isinstance(claims, list):
        raise ValueError("The model output did not contain a claims list.")

    validated = []
    for item in claims:
        if not isinstance(item, dict):
            raise ValueError("A model claim was not an object.")
        chunk_id = item.get("chunk_id")
        chunk = chunk_map.get(chunk_id)
        claim_text = item.get("claim_text")
        quote = item.get("evidence_quote")
        claim_type = item.get("claim_type")
        if chunk is None or not isinstance(claim_text, str) or not claim_text.strip() or len(claim_text) > 700:
            raise ValueError("A model claim was missing required text or a valid source chunk.")
        if claim_type not in CLAIM_TYPES or not isinstance(quote, str) or not quote.strip():
            raise ValueError("A model claim had an invalid type or empty evidence quote.")
        if not quote_is_present(chunk.content, quote):
            raise ValueError("A model quote was not present in its cited chunk.")
        owner = item.get("owner")
        due_date = item.get("due_date")
        validated.append({
            "claim_text": claim_text.strip(),
            "claim_type": claim_type,
            "owner": owner.strip()[:160] if isinstance(owner, str) and owner.strip() else None,
            "due_date": due_date.strip()[:80] if isinstance(due_date, str) and due_date.strip() else None,
            "evidence_quote": quote,
            "chunk_id": chunk_id,
        })
    return validated


def _claim_id(source_id: str, item: dict) -> str:
    key = "\0".join((source_id, item["chunk_id"], item["claim_type"], item["claim_text"], item["evidence_quote"]))
    return __import__("hashlib").sha256(key.encode("utf-8")).hexdigest()


def extract_all(session: Session, api_key: str | None = None, model: str | None = None) -> ExtractionSummary:
    summary = ExtractionSummary()
    sources = list(session.scalars(select(Source).order_by(Source.created_at)))
    key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
    selected_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    for source in sources:
        if source.access_level == "restricted":
            summary.skipped_restricted += 1
            continue
        chunks = list(source.chunks)
        if not chunks:
            continue
        extraction_mode = "local"
        if key:
            try:
                extracted = _call_responses_api(chunks, key, selected_model)
                extraction_mode = "model"
                summary.model += 1
            except (OSError, TimeoutError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                extracted = deterministic_claims(chunks)
                extraction_mode = "local"
                summary.local += 1
                summary.model_errors += 1
                summary.model_error_message = str(exc)[:300]
        else:
            extracted = deterministic_claims(chunks)
            summary.local += 1

        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        for item in extracted:
            cited_chunk = chunks_by_id.get(item["chunk_id"])
            if cited_chunk is None or not quote_is_present(cited_chunk.content, item["evidence_quote"]):
                continue
            duplicate = session.scalar(select(Claim.claim_id).where(
                Claim.source_id == source.source_id,
                Claim.chunk_id == item["chunk_id"],
                Claim.claim_text == item["claim_text"],
                Claim.evidence_quote == item["evidence_quote"],
            ).limit(1))
            if duplicate:
                continue
            session.add(Claim(
                claim_id=_claim_id(source.source_id, item),
                source_id=source.source_id,
                chunk_id=item["chunk_id"],
                claim_text=item["claim_text"],
                claim_type=item["claim_type"],
                owner=item["owner"],
                due_date=item["due_date"],
                evidence_quote=item["evidence_quote"],
                evidence_status="matched",
                review_status="pending",
                extraction_mode=extraction_mode,
            ))
            summary.created += 1
    return summary


def review_claim(
    session: Session,
    claim: Claim,
    *,
    action: str,
    claim_text: str,
    claim_type: str,
    owner: str,
    due_date: str,
    evidence_quote: str,
    reviewer_note: str,
) -> tuple[bool, str]:
    allowed_actions = {"save", "approve", "reject"}
    if action not in allowed_actions:
        return False, "Choose a valid review action."
    if not claim_text.strip() or len(claim_text) > 700:
        return False, "Claim text must be between 1 and 700 characters."
    if claim_type not in CLAIM_TYPES:
        return False, "Choose a valid claim category."
    if len(evidence_quote) > 2500:
        return False, "Evidence quote must be 2,500 characters or fewer."

    claim.claim_text = claim_text.strip()
    claim.claim_type = claim_type
    claim.owner = owner.strip()[:160] or None
    claim.due_date = due_date.strip()[:80] or None
    claim.evidence_quote = evidence_quote.strip()
    claim.evidence_status = "matched" if quote_is_present(claim.chunk.content, claim.evidence_quote) else "mismatch"
    claim.reviewer_note = reviewer_note.strip()[:1000] or None

    if action == "approve" and claim.evidence_status != "matched":
        claim.review_status = "pending"
        return False, "This claim stays pending because its quote is missing or mismatched."
    claim.review_status = {"save": "pending", "approve": "approved", "reject": "rejected"}[action]
    return True, {"save": "Review changes saved.", "approve": "Claim approved.", "reject": "Claim rejected."}[action]

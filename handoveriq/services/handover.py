from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import Claim, Source
from .permissions import load_incoming_claims, load_safe_pending_count

KIND_LABELS = {
    "decision": "Decisions",
    "owner": "Ownership",
    "open_action": "Open actions",
    "risk": "Risks and blockers",
    "dependency": "Dependencies",
    "date": "Dates",
    "question": "Questions to resolve",
    "context": "Project context",
}


def build_handover(session: Session) -> dict:
    claims = load_incoming_claims(session)
    groups: dict[str, list[Claim]] = defaultdict(list)
    for claim in claims:
        groups[claim.claim_type].append(claim)

    approved_open_actions = groups.get("open_action", [])
    week_one = [
        {
            "text": "Read the approved decisions and confirm the current project priority with the club lead.",
            "source_fact": False,
        }
    ]
    week_two = [
        {
            "text": "Check the listed dependencies and agree who owns the next milestone.",
            "source_fact": False,
        }
    ]
    for action in approved_open_actions[:2]:
        week_one.append({
            "text": action.claim_text,
            "source_fact": True,
            "claim": action,
        })
    for action in approved_open_actions[2:4]:
        week_two.append({
            "text": action.claim_text,
            "source_fact": True,
            "claim": action,
        })

    return {
        "claims": claims,
        "groups": groups,
        "labels": KIND_LABELS,
        "visible_count": len(claims),
        "open_action_count": len(approved_open_actions),
        "pending_count": load_safe_pending_count(session),
        "week_one": week_one,
        "week_two": week_two,
    }


def load_reviewer_claims(session: Session, status: str = "all") -> list[Claim]:
    statement = select(Claim).options(joinedload(Claim.source), joinedload(Claim.chunk))
    if status in {"pending", "approved", "rejected"}:
        statement = statement.where(Claim.review_status == status)
    return list(session.scalars(statement.order_by(Claim.created_at.desc())))


def source_claims(session: Session, source_id: str) -> list[Claim]:
    return list(session.scalars(
        select(Claim)
        .options(joinedload(Claim.source), joinedload(Claim.chunk))
        .where(Claim.source_id == source_id)
        .order_by(Claim.created_at)
    ))


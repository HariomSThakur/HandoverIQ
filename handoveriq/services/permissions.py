from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..models import Claim, Source
from .ingest import ACCESS_RANK


INCOMING_MAX_LEVEL = "team"


def can_view_level(access_level: str, role: str) -> bool:
    if role == "reviewer":
        return access_level in ACCESS_RANK
    if role == "incoming":
        return access_level in ACCESS_RANK and ACCESS_RANK[access_level] <= ACCESS_RANK[INCOMING_MAX_LEVEL]
    return False


def incoming_claims_statement():
    """Filter at the database query so restricted rows never reach the view model."""
    return (
        select(Claim)
        .join(Claim.source)
        .options(joinedload(Claim.source), joinedload(Claim.chunk))
        .where(
            Source.access_level.in_(("public", "team")),
            Claim.review_status == "approved",
            Claim.evidence_status == "matched",
        )
    )


def load_incoming_claims(session: Session) -> list[Claim]:
    return list(session.scalars(incoming_claims_statement().order_by(Claim.claim_type, Claim.created_at)))


def load_safe_pending_count(session: Session) -> int:
    statement = (
        select(func.count())
        .select_from(Claim)
        .join(Claim.source)
        .where(Source.access_level.in_(("public", "team")), Claim.review_status == "pending")
    )
    return session.scalar(statement) or 0


def source_for_role(session: Session, source_id: str, role: str) -> Source | None:
    statement = select(Source).where(Source.source_id == source_id)
    if role == "incoming":
        statement = statement.where(Source.access_level.in_(("public", "team")))
    elif role == "reviewer":
        statement = statement.where(Source.access_level.in_(tuple(ACCESS_RANK)))
    else:
        return None
    return session.scalar(statement)

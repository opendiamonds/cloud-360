"""EstimateSet visibility — owner + share list only (BR2.5 / FR7.3).

Does not import collab_router private helpers; diagram_id is never consulted.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import EstimateSet, EstimateShare


def is_owner(estimate_set: EstimateSet, user_id: int) -> bool:
    return int(estimate_set.owner_user_id) == int(user_id)


def is_shared_with(db: Session, estimate_set_id: int, user_id: int) -> bool:
    row = (
        db.query(EstimateShare)
        .filter(
            EstimateShare.estimate_set_id == estimate_set_id,
            EstimateShare.user_id == user_id,
        )
        .first()
    )
    return row is not None


def can_view_set(db: Session, estimate_set: EstimateSet, user_id: int) -> bool:
    if is_owner(estimate_set, user_id):
        return True
    return is_shared_with(db, estimate_set.id, user_id)


def get_visible_set(
    db: Session, set_id: int, user_id: int
) -> EstimateSet | None:
    row = db.query(EstimateSet).filter(EstimateSet.id == set_id).first()
    if row is None:
        return None
    if not can_view_set(db, row, user_id):
        return None
    return row


def list_visible_set_ids(db: Session, user_id: int) -> list[int]:
    owned = (
        db.query(EstimateSet.id)
        .filter(EstimateSet.owner_user_id == user_id)
        .all()
    )
    shared = (
        db.query(EstimateShare.estimate_set_id)
        .filter(EstimateShare.user_id == user_id)
        .all()
    )
    ids = {int(r[0]) for r in owned} | {int(r[0]) for r in shared}
    return sorted(ids)

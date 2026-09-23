import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session
from strawberry.dataloader import DataLoader

from app.models import Approval, AuditEvent, User


class Loaders:
    def __init__(self, db: Session):
        self.db = db
        self.users = DataLoader(load_fn=self._load_users)
        self.approvals = DataLoader(load_fn=self._load_approvals)
        self.audit_events = DataLoader(load_fn=self._load_audit_events)

    async def _load_users(self, ids: list[uuid.UUID]) -> list[User | None]:
        users = list(self.db.scalars(select(User).where(User.id.in_(ids))))
        by_id = {user.id: user for user in users}
        return [by_id.get(user_id) for user_id in ids]

    async def _load_approvals(self, change_request_ids: list[uuid.UUID]) -> list[list[Approval]]:
        rows = list(
            self.db.scalars(
                select(Approval)
                .where(Approval.change_request_id.in_(change_request_ids))
                .order_by(Approval.decided_at.asc(), Approval.id.asc())
            )
        )
        grouped: dict[uuid.UUID, list[Approval]] = defaultdict(list)
        for row in rows:
            grouped[row.change_request_id].append(row)
        return [grouped.get(change_request_id, []) for change_request_id in change_request_ids]

    async def _load_audit_events(
        self, change_request_ids: list[uuid.UUID]
    ) -> list[list[AuditEvent]]:
        rows = list(
            self.db.scalars(
                select(AuditEvent)
                .where(AuditEvent.change_request_id.in_(change_request_ids))
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            )
        )
        grouped: dict[uuid.UUID, list[AuditEvent]] = defaultdict(list)
        for row in rows:
            grouped[row.change_request_id].append(row)
        return [grouped.get(change_request_id, []) for change_request_id in change_request_ids]

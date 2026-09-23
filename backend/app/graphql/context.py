import uuid
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session
from strawberry.fastapi import BaseContext

from app.database import SessionLocal
from app.graphql.loaders import Loaders
from app.models import User
from app.security import decode_access_token


class Context(BaseContext):
    def __init__(self, user: User | None, db: Session, loaders: Loaders):
        super().__init__()
        self.user = user
        self.db = db
        self.loaders = loaders


def _resolve_user(db: Session, request: Request) -> User | None:
    header = request.headers.get("Authorization")
    if header is None or not header.startswith("Bearer "):
        return None
    subject = decode_access_token(header.removeprefix("Bearer "))
    if subject is None:
        return None
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        return None
    return db.get(User, user_id)


def get_graphql_context(request: Request) -> Iterator[Context]:
    db = SessionLocal()
    try:
        yield Context(user=_resolve_user(db, request), db=db, loaders=Loaders(db))
    finally:
        db.close()

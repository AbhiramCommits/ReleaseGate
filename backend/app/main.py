import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import get_db
from app.graphql import graphql_app
from app.logging import request_id_var, setup_logging
from app.models import User
from app.routers import analytics
from app.routers import change_requests as change_requests_router
from app.schemas import LoginRequest, TokenResponse
from app.security import create_access_token, verify_password
from app.workflow import InvalidTransition, PermissionDenied

setup_logging()

logger = logging.getLogger("app")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.getLogger("uvicorn.access").disabled = True
    yield


app = FastAPI(title="ReleaseGate API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def problem_response(
    status_code: int,
    title: str,
    detail: str | None = None,
    instance: str | None = None,
    extensions: dict | None = None,
) -> JSONResponse:
    payload: dict = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
    }
    if detail is not None:
        payload["detail"] = detail
    if instance is not None:
        payload["instance"] = instance
    if extensions:
        payload.update(extensions)
    return JSONResponse(
        status_code=status_code,
        content=payload,
        media_type="application/problem+json",
    )


@auth_router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=create_access_token(str(user.id)))


@app.get("/healthz")
def healthz(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    title = "Server error" if exc.status_code >= 500 else "Request failed"
    return problem_response(
        exc.status_code,
        title,
        detail=str(exc.detail),
        instance=request.url.path,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return problem_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Request validation failed",
        detail="The request body or parameters are invalid.",
        instance=request.url.path,
        extensions={"errors": exc.errors()},
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    return problem_response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Too many requests",
        detail=str(exc.detail),
        instance=request.url.path,
    )


@app.exception_handler(InvalidTransition)
async def invalid_transition_handler(request: Request, exc: InvalidTransition) -> JSONResponse:
    return problem_response(
        status.HTTP_409_CONFLICT,
        "Invalid transition",
        detail=str(exc),
        instance=request.url.path,
    )


@app.exception_handler(PermissionDenied)
async def permission_denied_handler(request: Request, exc: PermissionDenied) -> JSONResponse:
    return problem_response(
        status.HTTP_403_FORBIDDEN,
        "Permission denied",
        detail=str(exc),
        instance=request.url.path,
    )


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        logger.exception("Unhandled error while processing request")
        response = problem_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            detail="An unexpected error occurred.",
            instance=request.url.path,
        )
    finally:
        request_id_var.reset(token)
    response.headers["X-Request-Id"] = request_id
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(change_requests_router.router)
app.include_router(analytics.router)
app.include_router(graphql_app, prefix="/graphql")

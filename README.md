# ReleaseGate

Engineering change request (ECR) management platform with role-based review workflows,
audit logging, and analytics-ready data.

## Monorepo layout

```
releasegate/
  backend/    FastAPI + Strawberry GraphQL + SQLAlchemy 2.x + Alembic
  frontend/   React 18 + TypeScript + Vite
  docker-compose.yml
  README.md
```

## Stack

| Layer    | Tech                                                                 |
| -------- | -------------------------------------------------------------------- |
| Backend  | Python 3.11, FastAPI, Strawberry GraphQL, SQLAlchemy 2.x, Alembic    |
| Database | PostgreSQL 15                                                        |
| Frontend | React 18, TypeScript (strict), Vite, React Router, TanStack Query    |

## Quick start (Docker)

Bring up the whole stack with one command:

```sh
docker compose up --build
```

| Service  | URL                                    |
| -------- | -------------------------------------- |
| Frontend | http://localhost:3000                  |
| API docs | http://localhost:8003/docs             |
| GraphQL  | http://localhost:8003/graphql          |
| Health   | http://localhost:8003/healthz          |

The backend container runs `alembic upgrade head` and `python -m app.seed` on startup, so the
database is migrated and seeded automatically. Seed data is idempotent and skipped on restart.

### Seeded users

| Email                     | Role      | Password     |
| ------------------------- | --------- | ------------ |
| requester@releasegate.dev | REQUESTER | password123  |
| reviewer@releasegate.dev  | REVIEWER  | password123  |
| admin@releasegate.dev     | ADMIN     | password123  |

The seed also creates ~40 change requests (`ECR-1000` ... `ECR-1039`) spread across all stages
with timestamps backdated over 90 days, plus matching approvals and audit events.

## Local development

### 1. Database

Run only PostgreSQL (published on port 5435):

```sh
docker compose up -d db
```

Host ports are configurable via `DB_PORT`, `BACKEND_PORT`, and `FRONTEND_PORT`
(see `docker-compose.yml`). The commands below assume the defaults
(db on 5435, API on 8003, frontend on 3000).

### 2. Backend (uv)

```sh
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8003
```

Fallback without uv (pip):

```sh
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8003
```

### 3. Frontend

```sh
cd frontend
npm install
npm run dev
```

Vite proxies `/auth`, `/healthz`, and `/graphql` to `http://localhost:8003`.
Open http://localhost:5173 and sign in with one of the seeded users above.

The frontend talks to the GraphQL API. TypeScript types and typed TanStack Query hooks
are generated from `frontend/schema.graphql` with graphql-codegen
(`npm run codegen`), and regeneration is part of `npm run build`.

### 4. GraphQL schema sync

`backend/schema.graphql` is the exported SDL. `make schema` (from the repo root)
regenerates it and copies it to `frontend/schema.graphql`. A backend test asserts the
committed file always matches the live schema.

```sh
make schema
```

## Testing

All targets run from the repo root (delegate to `backend/Makefile` and `frontend` npm scripts):

```sh
make test   # backend pytest (coverage >= 80%, dockerized Postgres) + frontend vitest
make lint   # ruff + mypy + eslint + tsc --noEmit
make fmt    # ruff format + prettier
make e2e    # Playwright workflow test (requires Docker)
```

Backend tests never use SQLite: the suite boots an ephemeral `postgres:15` Docker
container, runs Alembic migrations against it, and truncates tables between tests.
Coverage targets `app/workflow.py`, the repository/service layer (`app/repositories`),
and the API layer (`app/routers`, `app/graphql`) — all >= 80%.

Frontend tests use Vitest + React Testing Library + MSW (mock the GraphQL endpoint),
and one Playwright end-to-end test drives the real stack: requester creates and
submits, then the reviewer approves through both review stages.

## API

REST:

| Method | Path                                    | Description                                                  |
| ------ | --------------------------------------- | ------------------------------------------------------------ |
| POST   | `/auth/login`                           | `{ "email", "password" }` -> `{ "access_token", "token_type" }` |
| GET    | `/healthz`                              | `{"status":"ok","db":"ok"}` after a real `SELECT 1`          |
| GET    | `/api/v1/change-requests`               | List requests; filters: `stage`, `risk_level`, `requester_id`, `subsystem`; offset pagination (`offset`, `limit`), sorted by `updated_at` desc |
| POST   | `/api/v1/change-requests`               | Create a request (starts in DRAFT)                           |
| GET    | `/api/v1/change-requests/{id}`          | Get one request                                              |
| PATCH  | `/api/v1/change-requests/{id}`          | Update request fields; requester-owner only, DRAFT only      |
| POST   | `/api/v1/change-requests/{id}/transitions` | `{ "action": "SUBMIT\|APPROVE\|REQUEST_CHANGES\|REJECT", "comment" }`; runs the state machine |
| GET    | `/api/v1/change-requests/{id}/audit`    | Full ordered audit trail                                     |
| GET    | `/api/v1/analytics/cycle-time`          | Per-stage dwell-time stats, current stage counts, end-to-end latency, slowest stages |

GraphQL (`/graphql`, GraphiQL enabled in dev via `ENABLE_GRAPHIQL`):

- Queries: `me`, `changeRequest(id)`, `changeRequests(stage, riskLevel, subsystem, first, after)`
  (Relay-style connection with `pageInfo` and cursors), `cycleTimeAnalytics`
- Mutations: `createChangeRequest`, `updateChangeRequest`, `transitionChangeRequest(id, action, comment)`
- The same repository/service layer backs GraphQL and REST; workflow errors surface as
  GraphQL errors with `extensions.code` `PERMISSION_DENIED` (403) or `INVALID_TRANSITION` (409).
- Auth reads the JWT from the `Authorization` header per request. Unauthenticated access is
  rejected except for `__schema` (introspection). Requester/reviewer/actor lookups go through
  DataLoaders to avoid N+1 queries.

All `/api/v1` endpoints require `Authorization: Bearer <token>`.

JWT tokens are HS256-signed and carry the user id in the `sub` claim. Protected endpoints
use the `get_current_user` FastAPI dependency, which decodes the `Authorization: Bearer`
token and loads the user from the database.

Every request gets a request id (from the `X-Request-Id` header or generated), echoed back
in the `X-Request-Id` response header and included in the structured JSON logs.

## Workflow

State machine (see `backend/app/workflow.py`, pure functions):

```
DRAFT --SUBMIT (requester-owner)--> SUBMITTED --APPROVE (reviewer/admin)--> ENGINEERING_REVIEW
ENGINEERING_REVIEW --APPROVE--> MANUFACTURING_REVIEW    (HIGH risk needs two distinct reviewers)
ENGINEERING_REVIEW --REQUEST_CHANGES--> DRAFT
MANUFACTURING_REVIEW --APPROVE--> APPROVED (terminal)
MANUFACTURING_REVIEW --REQUEST_CHANGES--> DRAFT
ENGINEERING_REVIEW | MANUFACTURING_REVIEW --REJECT--> REJECTED (terminal)
```

Rule violations: `InvalidTransition` -> 409, `PermissionDenied` -> 403. Reviewers cannot
approve a request twice at the same stage and cannot approve their own requests. Each
transition commits atomically: approval row + stage update + audit event.

## Database schema

- `users` - id (UUID), email (unique), full_name, hashed_password, role enum
  (REQUESTER | REVIEWER | ADMIN), created_at
- `change_requests` - id (UUID), ticket_key (unique, e.g. `ECR-1042`), title, description,
  vehicle_program, subsystem, risk_level enum (LOW | MEDIUM | HIGH), current_stage enum
  (DRAFT | SUBMITTED | ENGINEERING_REVIEW | MANUFACTURING_REVIEW | APPROVED | REJECTED),
  requester_id FK, created_at, updated_at
- `approvals` - id (UUID), change_request_id FK, stage enum, reviewer_id FK, decision enum
  (APPROVE | REJECT | REQUEST_CHANGES), comment, decided_at
- `audit_events` - id (UUID), change_request_id FK, actor_id FK, from_stage, to_stage,
  action, metadata (JSONB), created_at. Append-only: never updated or deleted.

Indexes: `change_requests(current_stage)`, `change_requests(requester_id)`,
`audit_events(change_request_id, created_at)`.

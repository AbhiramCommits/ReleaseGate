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

## API

| Method | Path          | Description                                                  |
| ------ | ------------- | ------------------------------------------------------------ |
| POST   | `/auth/login` | `{ "email", "password" }` -> `{ "access_token", "token_type" }` |
| GET    | `/healthz`    | `{"status":"ok","db":"ok"}` after a real `SELECT 1`          |
| GET    | `/graphql`    | GraphQL endpoint (GraphiQL in development)                   |

JWT tokens are HS256-signed and carry the user id in the `sub` claim. Protected endpoints
use the `get_current_user` FastAPI dependency, which decodes the `Authorization: Bearer`
token and loads the user from the database.

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

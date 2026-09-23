# ADR-002: Validate transitions in pure functions, separate from persistence

- Status: accepted
- Date: 2026-09-23

## Context

Change requests move through a state machine with strict rules:

- Allowed transitions depend on the current stage and the actor's role.
- `HIGH` risk requests need two distinct reviewer approvals at ENGINEERING_REVIEW.
- A reviewer may not approve the same request twice at the same stage, nor their
  own request.
- `APPROVED`/`REJECTED` are terminal.

The rules must be enforced identically on every entry point (REST, GraphQL, and
anything added later), and they must be trivially testable.

## Decision

The state machine lives in `app/workflow.py` as pure functions that take plain
snapshots (`RequestSnapshot`, `ActorSnapshot`, `ApprovalRecord`) and return a
`Transition` dataclass, raising `InvalidTransition` or `PermissionDenied` on
violations. It imports nothing from the database layer — not the engine, not the
session, not the ORM models (enums live in `app/enums.py` for this reason).

The repository composes the workflow: it loads the current state and existing
approvals, calls the pure function, and only then writes the approval row, the
audit event, and the new stage inside one transaction.

## Tradeoffs

| Approach | Pros | Cons |
| --- | --- | --- |
| Rules inside route handlers | Fewer files | Duplicated across REST + GraphQL; untestable without a database |
| Rules as SQLAlchemy model/event logic | Persistence-adjacent | Ties rules to the ORM; hard to unit test; implicit behavior |
| **Pure functions (chosen)** | Deterministic, exhaustively unit-testable (every allowed + 15 rejected cases), reusable by any caller, impossible to bypass accidentally | The caller must pass correct snapshots; the repository owns the read-then-write ordering (mitigated by `SELECT ... FOR UPDATE` and a single commit) |

## Consequences

- Positive: 96 backend tests include a complete unit matrix of the state machine
  with no database; API-level tests then only verify wiring and error mapping
  (403/409 problem+json).
- Positive: the same exceptions map cleanly onto HTTP (409/403) and GraphQL
  (`extensions.code` `INVALID_TRANSITION`/`PERMISSION_DENIED`).
- Positive: adding a transition later is a one-place change, covered by unit tests
  and automatically enforced everywhere.
- Negative: the module must stay pure — enforced by review and by the fact it
  imports nothing from `app.database`.

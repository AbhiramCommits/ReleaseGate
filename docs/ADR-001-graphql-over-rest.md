# ADR-001: Layer GraphQL over the REST service layer instead of replacing it

- Status: accepted
- Date: 2026-09-23

## Context

ReleaseGate needs both a REST surface (per the original product spec: list/create/
patch/transition endpoints under `/api/v1`) and a GraphQL surface (typed end-to-end
frontend, Relay-style pagination, analytics). Both surfaces manipulate the same
domain: change requests, approvals, audit events, and the workflow state machine.

Two ways to get there:

1. **Replace REST with GraphQL** and have the frontend talk GraphQL only.
2. **Layer GraphQL over the existing service layer** so both APIs share one
   source of truth for business logic.

## Decision

We chose option 2. GraphQL resolvers call the exact same repository/service
functions the REST routers call (`app/repositories/change_requests.py`,
`app/repositories/analytics.py`), and the workflow module
(`app/workflow.py`) is pure and shared by both. Mutations reuse the same
transactional `transition_change_request` path, so approval + audit + stage
update remain atomic regardless of which API performed the transition.

## Tradeoffs

| Approach | Pros | Cons |
| --- | --- | --- |
| GraphQL replaces REST | Single API, smaller surface | Breaks the product spec; forces every consumer onto GraphQL; no escape hatch for simple clients (curl, scripts, health checks) |
| **GraphQL layered over REST (chosen)** | One business-logic source of truth; no duplicated validation/state-machine code; both APIs get every fix at once; REST stays for simple integrations and health/ops tooling | Two API surfaces to document and keep in sync; schema + docs must stay aligned (enforced by the SDL export test) |

## Consequences

- Positive: workflow rules (dual approval, self-approval ban, terminal stages) are
  enforced identically on both surfaces; the repository layer stays the only place
  that touches persistence.
- Positive: the frontend ships typed end-to-end via graphql-codegen against the
  committed SDL (`backend/schema.graphql`), with a test asserting the file matches
  the live schema.
- Negative: pagination semantics differ (offset for REST, cursor/Relay for GraphQL),
  so the repository exposes both while sharing the same filter construction.
- Negative: the GraphQL surface needs its own auth wiring (per-request JWT in the
  Strawberry context) and its own N+1 protection (DataLoaders), because it resolves
  relations per query shape rather than per endpoint.

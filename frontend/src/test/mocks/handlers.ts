import {
  graphql,
  HttpResponse,
  type DefaultBodyType,
  type GraphQLResponseBody,
} from "msw";

export const gql = graphql.link("http://localhost:3000/graphql");

export const EMPTY_CONNECTION = {
  edges: [],
  pageInfo: {
    hasNextPage: false,
    hasPreviousPage: false,
    startCursor: null,
    endCursor: null,
  },
  totalCount: 0,
};

export function okResponse<TData extends DefaultBodyType>(data: TData) {
  return HttpResponse.json<GraphQLResponseBody<TData>>({ data });
}

export function meHandler(role: string, id = "me-1") {
  return gql.query("Me", () =>
    okResponse({
      me: {
        id,
        email: `${role.toLowerCase()}@test.dev`,
        fullName: `${role} User`,
        role,
      },
    }),
  );
}

export function detailHandler(detail: Record<string, unknown>) {
  return gql.query("ChangeRequestDetail", () =>
    okResponse({ changeRequest: detail }),
  );
}

export function detailFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: "req-1",
    ticketKey: "ECR-9001",
    title: "Test request",
    description: "Description body.",
    vehicleProgram: "Voyager",
    subsystem: "Chassis",
    riskLevel: "MEDIUM",
    currentStage: "DRAFT",
    requesterId: "owner-1",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-02T00:00:00Z",
    requester: {
      id: "owner-1",
      fullName: "Owner User",
      email: "owner@test.dev",
      role: "REQUESTER",
    },
    approvals: [],
    auditEvents: [],
    ...overrides,
  };
}

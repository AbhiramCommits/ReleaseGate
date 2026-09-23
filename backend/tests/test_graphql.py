import pytest
from httpx import AsyncClient
from sqlalchemy import event

from app.enums import ChangeStage, Role
from app.security import create_access_token


@pytest.fixture
def auth_headers(requester) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(requester.id))}"}


async def gql(client: AsyncClient, query: str, variables=None, headers=None):
    body: dict = {"query": query}
    if variables is not None:
        body["variables"] = variables
    return await client.post("/graphql", json=body, headers=headers or {})


class TestGraphQLAuth:
    async def test_unauthenticated_query_rejected_but_schema_allowed(self, client):
        introspection = await gql(
            client, "{ __schema { queryType { name } mutationType { name } } }"
        )
        assert introspection.status_code == 200
        assert "errors" not in introspection.json()

        rejected = await gql(client, "{ me { id } }")
        assert rejected.status_code == 200
        body = rejected.json()
        assert body["data"] is None or body["data"].get("me") is None
        error = body["errors"][0]
        assert error["extensions"]["code"] == "UNAUTHENTICATED"

    async def test_invalid_token_rejected(self, client):
        response = await gql(client, "{ me { id } }", headers={"Authorization": "Bearer garbage"})
        assert response.json()["errors"][0]["extensions"]["code"] == "UNAUTHENTICATED"


class TestGraphQLQueries:
    async def test_me_query(self, client, requester, auth_headers):
        response = await gql(client, "{ me { id email fullName role } }", headers=auth_headers)
        body = response.json()
        assert body["data"]["me"]["email"] == requester.email
        assert body["data"]["me"]["role"] == "REQUESTER"

    async def test_change_request_detail_with_nested_fields(
        self, client, requester, make_change_request, auth_headers
    ):
        cr = make_change_request(requester, stage=ChangeStage.SUBMITTED)
        response = await gql(
            client,
            """
            query($id: ID!) {
              changeRequest(id: $id) {
                ticketKey currentStage
                requester { email role }
                approvals { id }
                auditEvents { action }
              }
            }
            """,
            {"id": str(cr.id)},
            auth_headers,
        )
        data = response.json()["data"]["changeRequest"]
        assert data["ticketKey"] == cr.ticket_key
        assert data["currentStage"] == "SUBMITTED"
        assert data["requester"]["email"] == requester.email
        assert [event["action"] for event in data["auditEvents"]] == [
            "CREATED",
            "SUBMITTED",
        ]

    async def test_change_requests_connection_pagination(
        self, client, requester, make_change_request, auth_headers
    ):
        for index in range(5):
            make_change_request(requester, title=f"Page {index}", ticket_key=f"ECR-{6000 + index}")

        first = await gql(
            client,
            """
            query($first: Int) {
              changeRequests(first: $first) {
                edges { cursor node { ticketKey } }
                pageInfo { hasNextPage hasPreviousPage endCursor }
                totalCount
              }
            }
            """,
            {"first": 2},
            auth_headers,
        )
        body = first.json()["data"]["changeRequests"]
        assert body["totalCount"] == 5
        assert len(body["edges"]) == 2
        assert body["pageInfo"]["hasNextPage"] is True

        second = await gql(
            client,
            """
            query($first: Int, $after: String) {
              changeRequests(first: $first, after: $after) {
                edges { cursor node { ticketKey } }
                pageInfo { hasNextPage hasPreviousPage }
              }
            }
            """,
            {"first": 2, "after": body["pageInfo"]["endCursor"]},
            auth_headers,
        )
        second_body = second.json()["data"]["changeRequests"]
        assert second_body["pageInfo"]["hasPreviousPage"] is True
        first_keys = [edge["node"]["ticketKey"] for edge in body["edges"]]
        second_keys = [edge["node"]["ticketKey"] for edge in second_body["edges"]]
        assert not set(first_keys) & set(second_keys)

    async def test_invalid_cursor_rejected(self, client, auth_headers):
        response = await gql(
            client,
            "query($after: String) { changeRequests(after: $after) { edges { cursor } } }",
            {"after": "not-base64!!!"},
            auth_headers,
        )
        assert response.json()["errors"][0]["extensions"]["code"] == "BAD_USER_INPUT"

    async def test_missing_change_request_returns_null(self, client, auth_headers):
        response = await gql(
            client,
            'query { changeRequest(id: "00000000-0000-0000-0000-000000000000") { id } }',
            headers=auth_headers,
        )
        assert response.json()["data"]["changeRequest"] is None


class TestGraphQLMutations:
    async def test_create_change_request_mutation(self, client, requester, auth_headers):
        response = await gql(
            client,
            """
            mutation($input: ChangeRequestInput!) {
              createChangeRequest(input: $input) { id ticketKey currentStage requester { id } }
            }
            """,
            {
                "input": {
                    "title": "GraphQL mutation test",
                    "description": "created via test",
                    "vehicleProgram": "Nimbus",
                    "subsystem": "Thermal",
                    "riskLevel": "MEDIUM",
                }
            },
            auth_headers,
        )
        data = response.json()["data"]["createChangeRequest"]
        assert data["currentStage"] == "DRAFT"
        assert data["requester"]["id"] == str(requester.id)

    async def test_transition_mutation_and_workflow_errors(
        self, client, requester, make_user, make_change_request, auth_headers
    ):
        from app.security import create_access_token

        reviewer = make_user(Role.REVIEWER)
        reviewer_headers = {"Authorization": f"Bearer {create_access_token(str(reviewer.id))}"}
        cr = make_change_request(requester, stage=ChangeStage.SUBMITTED)

        denied = await gql(
            client,
            "mutation($id: ID!) { transitionChangeRequest(id: $id, action: APPROVE) { id } }",
            {"id": str(cr.id)},
            auth_headers,
        )
        error = denied.json()["errors"][0]
        assert error["extensions"]["code"] == "PERMISSION_DENIED"

        approved = await gql(
            client,
            "mutation($id: ID!) { transitionChangeRequest(id: $id, action: APPROVE) { currentStage } }",
            {"id": str(cr.id)},
            reviewer_headers,
        )
        assert approved.json()["data"]["transitionChangeRequest"]["currentStage"] == (
            "ENGINEERING_REVIEW"
        )

        invalid = await gql(
            client,
            "mutation($id: ID!) { transitionChangeRequest(id: $id, action: SUBMIT) { id } }",
            {"id": str(cr.id)},
            reviewer_headers,
        )
        assert invalid.json()["errors"][0]["extensions"]["code"] == "INVALID_TRANSITION"

    async def test_update_change_request_mutation(
        self, client, requester, make_change_request, auth_headers
    ):
        cr = make_change_request(requester, stage=ChangeStage.DRAFT)
        response = await gql(
            client,
            """
            mutation($id: ID!, $input: ChangeRequestUpdateInput!) {
              updateChangeRequest(id: $id, input: $input) { title riskLevel }
            }
            """,
            {"id": str(cr.id), "input": {"title": "Updated via GraphQL"}},
            auth_headers,
        )
        data = response.json()["data"]["updateChangeRequest"]
        assert data["title"] == "Updated via GraphQL"
        assert data["riskLevel"] == "MEDIUM"


class TestGraphQLDataLoaderBatching:
    async def test_query_count_constant_as_result_set_grows(
        self, client, requester, make_change_request, auth_headers
    ):
        from app.database import engine

        for index in range(3):
            make_change_request(requester, title=f"Batch {index}", ticket_key=f"ECR-{7000 + index}")

        queries: list[str] = []

        def capture(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)

        document = """
        query($first: Int!) {
          changeRequests(first: $first) {
            edges { node { id requester { id email } } }
          }
        }
        """

        event.listen(engine, "before_cursor_execute", capture)
        try:
            small = await gql(client, document, {"first": 3}, auth_headers)
            assert "errors" not in small.json()
            small_count = len(queries)

            queries.clear()
            for index in range(3, 12):
                make_change_request(
                    requester, title=f"Batch {index}", ticket_key=f"ECR-{7000 + index}"
                )
            queries.clear()

            large = await gql(client, document, {"first": 12}, auth_headers)
            assert "errors" not in large.json()
            large_count = len(queries)

            assert large_count == small_count

            user_batch_queries = [
                statement
                for statement in queries
                if "FROM users" in statement and " IN " in statement
            ]
            assert len(user_batch_queries) == 1
        finally:
            event.remove(engine, "before_cursor_execute", capture)

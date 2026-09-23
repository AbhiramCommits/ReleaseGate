from httpx import AsyncClient

from app.models import User
from app.security import create_access_token


def headers_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


async def post_login(client: AsyncClient, email: str, password: str = "password123"):
    return await client.post("/auth/login", json={"email": email, "password": password})


class TestRateLimiting:
    async def test_login_rate_limited_after_five_attempts(self, client, requester):
        for _ in range(5):
            response = await post_login(client, requester.email)
            assert response.status_code == 200

        blocked = await post_login(client, requester.email)
        assert blocked.status_code == 429
        assert blocked.headers["content-type"] == "application/problem+json"
        body = blocked.json()
        assert body["title"] == "Too many requests"
        assert body["status"] == 429


class TestProblemJson:
    async def test_unknown_route_returns_problem_json(self, client, requester):
        response = await client.get(
            "/api/v1/does-not-exist", headers=headers_for(requester)
        )
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/problem+json"
        body = response.json()
        assert body["type"] == "about:blank"
        assert body["title"] == "Request failed"
        assert body["status"] == 404
        assert body["instance"] == "/api/v1/does-not-exist"

    async def test_unauthorized_login_returns_problem_json(self, client, requester):
        response = await post_login(client, requester.email, password="wrong")
        assert response.status_code == 401
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["detail"] == "Invalid email or password"

    async def test_validation_error_returns_problem_json(self, client, requester):
        response = await client.post(
            "/api/v1/change-requests",
            json={"title": "", "description": "x", "vehicle_program": "p", "subsystem": "s", "risk_level": "MEDIUM"},
            headers=headers_for(requester),
        )
        assert response.status_code == 422
        assert response.headers["content-type"] == "application/problem+json"
        body = response.json()
        assert body["title"] == "Request validation failed"
        assert isinstance(body["errors"], list)

    async def test_workflow_conflict_returns_problem_json(self, client, requester, reviewer):
        created = await client.post(
            "/api/v1/change-requests",
            json={"title": "t", "description": "d", "vehicle_program": "p", "subsystem": "s", "risk_level": "MEDIUM"},
            headers=headers_for(requester),
        )
        cr_id = created.json()["id"]
        await client.post(
            f"/api/v1/change-requests/{cr_id}/transitions",
            json={"action": "SUBMIT"},
            headers=headers_for(requester),
        )
        conflict = await client.post(
            f"/api/v1/change-requests/{cr_id}/transitions",
            json={"action": "SUBMIT"},
            headers=headers_for(requester),
        )
        assert conflict.status_code == 409
        assert conflict.headers["content-type"] == "application/problem+json"
        assert conflict.json()["title"] == "Invalid transition"


class TestCors:
    async def test_allows_configured_origin(self, client):
        response = await client.options(
            "/healthz",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )

    async def test_rejects_unknown_origin(self, client):
        response = await client.options(
            "/healthz",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in response.headers


class TestGraphQLHardening:
    async def test_complexity_limit_rejects_alias_bomb(self, client, requester):
        nested = (
            "edges { node { requester { id } approvals { reviewer { id } } "
            "auditEvents { actor { id } } } }"
        )
        selections = " ".join(
            f"c{i}: changeRequests {{ {nested} }}" for i in range(5)
        )
        response = await client.post(
            "/graphql",
            json={"query": f"query {{ {selections} }}"},
            headers=headers_for(requester),
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("errors")
        assert "complexity" in body["errors"][0]["message"]

    async def test_normal_queries_within_limits(self, client, requester):
        response = await client.post(
            "/graphql",
            json={
                "query": """
                query {
                  changeRequests(first: 5) {
                    edges { node { id ticketKey currentStage requester { id } } }
                  }
                  cycleTimeAnalytics { stageMetrics { stage averageHours } }
                }
                """
            },
            headers=headers_for(requester),
        )
        assert response.status_code == 200
        assert "errors" not in response.json()


async def test_graphiql_disabled_in_production(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "environment", "production")
    assert settings.graphiql_enabled is False

    monkeypatch.setattr(settings, "environment", "development")
    assert settings.graphiql_enabled is True

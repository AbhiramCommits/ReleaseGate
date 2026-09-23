import strawberry
from strawberry.fastapi import GraphQLRouter


@strawberry.type
class Query:
    @strawberry.field
    def ping(self) -> str:
        return "pong"


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

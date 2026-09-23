import strawberry
from strawberry.fastapi import GraphQLRouter

from app.config import settings
from app.graphql.context import get_graphql_context
from app.graphql.schema import Mutation, Query

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphql_ide="graphiql" if settings.enable_graphiql else None,
)

__all__ = ["graphql_app", "schema"]

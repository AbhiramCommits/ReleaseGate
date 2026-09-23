import strawberry
from strawberry.extensions import AddValidationRules, MaxAliasesLimiter
from strawberry.fastapi import GraphQLRouter

from app.config import settings
from app.graphql.context import get_graphql_context
from app.graphql.schema import Mutation, Query
from app.graphql.validation import ComplexityRule, DepthLimitRule

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        lambda: AddValidationRules([DepthLimitRule, ComplexityRule]),
        lambda: MaxAliasesLimiter(max_alias_count=15),
    ],
)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphql_ide="graphiql" if settings.graphiql_enabled else None,
)

__all__ = ["graphql_app", "schema"]

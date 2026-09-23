from graphql import (
    GraphQLError,
    GraphQLField,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
    parse,
)
from graphql.language.visitor import visit
from graphql.utilities import TypeInfo
from graphql.validation import ValidationContext

from app.graphql.validation import ComplexityRule, DepthLimitRule

child_type = GraphQLObjectType("Child", {"name": GraphQLField(GraphQLString)})
node_type = GraphQLObjectType(
    "Node",
    {
        "child": GraphQLField(child_type),
        "children": GraphQLField(GraphQLNonNull(GraphQLList(GraphQLNonNull(child_type)))),
    },
)
query_type = GraphQLObjectType("Query", {"node": GraphQLField(node_type)})
schema = GraphQLSchema(query=query_type)


def apply_rule(document, rule_factory) -> list[GraphQLError]:
    errors: list[GraphQLError] = []
    context = ValidationContext(schema, document, TypeInfo(schema), errors.append)
    rule = rule_factory(context)
    visit(document, rule)
    return errors


class TestDepthLimitRule:
    def test_allows_queries_at_or_below_limit(self):
        document = parse("{ node { child { name } } }")
        errors = apply_rule(document, lambda ctx: DepthLimitRule(ctx, max_depth=3))
        assert errors == []

    def test_rejects_queries_deeper_than_limit(self):
        document = parse("{ node { child { name } } }")
        errors = apply_rule(document, lambda ctx: DepthLimitRule(ctx, max_depth=2))
        assert len(errors) == 1
        assert "depth" in errors[0].message


class TestComplexityRule:
    def test_list_fields_multiply_child_cost(self):
        document = parse("{ node { children { name } } }")
        allowed = apply_rule(document, lambda ctx: ComplexityRule(ctx, max_complexity=7))
        assert allowed == []
        rejected = apply_rule(document, lambda ctx: ComplexityRule(ctx, max_complexity=6))
        assert len(rejected) == 1
        assert "complexity" in rejected[0].message

    def test_scalar_only_query_is_cheap(self):
        document = parse("{ node { child { name } } }")
        errors = apply_rule(document, lambda ctx: ComplexityRule(ctx, max_complexity=3))
        assert errors == []

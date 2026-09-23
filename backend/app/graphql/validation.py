from graphql import GraphQLError
from graphql.language import FieldNode, OperationDefinitionNode
from graphql.type import GraphQLList, GraphQLNonNull, GraphQLObjectType
from graphql.validation import ASTValidationContext, ASTValidationRule

MAX_DEPTH = 10
MAX_COMPLEXITY = 300
LIST_FACTOR = 5


class DepthLimitRule(ASTValidationRule):
    def __init__(self, context: ASTValidationContext, max_depth: int = MAX_DEPTH):
        super().__init__(context)
        self.max_depth = max_depth

    def enter_operation_definition(self, node: OperationDefinitionNode, *args) -> None:
        depth = self._depth_of(node.selection_set, 0)
        if depth > self.max_depth:
            self.report_error(
                GraphQLError(
                    f"Query depth of {depth} exceeds the limit of {self.max_depth}.",
                    node,
                )
            )

    def _depth_of(self, selection_set, current_depth: int) -> int:
        max_depth = current_depth + 1
        for selection in selection_set.selections:
            if isinstance(selection, FieldNode) and selection.selection_set is not None:
                child_depth = self._depth_of(selection.selection_set, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        return max_depth


class ComplexityRule(ASTValidationRule):
    def __init__(self, context: ASTValidationContext, max_complexity: int = MAX_COMPLEXITY):
        super().__init__(context)
        self.max_complexity = max_complexity

    def enter_operation_definition(self, node: OperationDefinitionNode, *args) -> None:
        root_type = self.context.schema.get_root_type(node.operation)
        complexity = self._selection_complexity(node.selection_set, root_type)
        if complexity > self.max_complexity:
            self.report_error(
                GraphQLError(
                    f"Query complexity of {complexity} exceeds the limit of "
                    f"{self.max_complexity}.",
                    node,
                )
            )

    def _selection_complexity(self, selection_set, parent_type) -> int:
        total = 0
        for selection in selection_set.selections:
            if not isinstance(selection, FieldNode):
                continue
            total += self._field_complexity(selection, parent_type)
        return total

    def _field_complexity(self, field: FieldNode, parent_type) -> int:
        field_cost = 1
        if field.selection_set is None or parent_type is None:
            return field_cost
        field_def = parent_type.fields.get(field.name.value)
        multiplier = 1
        child_type = None
        if field_def is not None:
            field_type = field_def.type
            while isinstance(field_type, (GraphQLList, GraphQLNonNull)):
                if isinstance(field_type, GraphQLList):
                    multiplier = LIST_FACTOR
                field_type = field_type.of_type
            if isinstance(field_type, GraphQLObjectType):
                child_type = field_type
        child_cost = self._selection_complexity(field.selection_set, child_type)
        return field_cost + multiplier * child_cost

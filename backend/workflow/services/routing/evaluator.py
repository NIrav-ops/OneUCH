import ast

from workflow.services.routing.exceptions import (
    RoutingEvaluationError,
)


class SafeExpressionEvaluator(ast.NodeVisitor):
    """
    Safe evaluator for workflow routing expressions.

    Supported:

        ==
        !=
        >
        >=
        <
        <=

        and
        or
        not

        in
        not in

        true
        false
        null

    Example:

        priority == "high"

        amount > 50000

        department == "Finance"

        sender in ["CEO", "CFO"]
    """

    ALLOWED_COMPARE = (
        ast.Eq,
        ast.NotEq,
        ast.Gt,
        ast.GtE,
        ast.Lt,
        ast.LtE,
        ast.In,
        ast.NotIn,
    )

    def __init__(self, variables):

        self.variables = variables

    def evaluate(self, expression):

        if expression is None:
            return True

        expression = expression.strip()

        if expression == "":
            return True

        expression = (
            expression
            .replace("AND", "and")
            .replace("OR", "or")
            .replace("NOT", "not")
            .replace("true", "True")
            .replace("false", "False")
            .replace("null", "None")
        )

        tree = ast.parse(expression, mode="eval")

        return bool(self.visit(tree.body))

    def visit_Name(self, node):

        return self.variables.get(node.id)

    def visit_Constant(self, node):

        return node.value

    def visit_List(self, node):

        return [
            self.visit(v)
            for v in node.elts
        ]

    def visit_BoolOp(self, node):

        values = [
            self.visit(v)
            for v in node.values
        ]

        if isinstance(node.op, ast.And):
            return all(values)

        if isinstance(node.op, ast.Or):
            return any(values)

        raise RoutingEvaluationError(
            "Unsupported boolean operator."
        )

    def visit_UnaryOp(self, node):

        if isinstance(node.op, ast.Not):
            return not self.visit(node.operand)

        raise RoutingEvaluationError(
            "Unsupported unary operator."
        )

    def visit_Compare(self, node):

        left = self.visit(node.left)

        for op, comparator in zip(
            node.ops,
            node.comparators,
        ):

            right = self.visit(comparator)

            if not isinstance(
                op,
                self.ALLOWED_COMPARE,
            ):
                raise RoutingEvaluationError(
                    "Unsupported comparison."
                )

            if isinstance(op, ast.Eq):
                ok = left == right

            elif isinstance(op, ast.NotEq):
                ok = left != right

            elif isinstance(op, ast.Gt):
                ok = left > right

            elif isinstance(op, ast.GtE):
                ok = left >= right

            elif isinstance(op, ast.Lt):
                ok = left < right

            elif isinstance(op, ast.LtE):
                ok = left <= right

            elif isinstance(op, ast.In):
                ok = left in right

            elif isinstance(op, ast.NotIn):
                ok = left not in right

            else:
                ok = False

            if not ok:
                return False

            left = right

        return True

    def generic_visit(self, node):

        raise RoutingEvaluationError(
            f"Unsupported expression: {type(node).__name__}"
        )


class RoutingEvaluator:
    """
    Enterprise routing evaluator.

    Responsible only for evaluating
    transition conditions.

    Runtime selection is added
    in Commit 11.4.1B.
    """

    @classmethod
    def evaluate(
        cls,
        condition,
        variables,
    ):

        evaluator = SafeExpressionEvaluator(
            variables
        )

        return evaluator.evaluate(condition)
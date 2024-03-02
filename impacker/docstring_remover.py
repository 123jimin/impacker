import ast

class DocstringRemover(ast.NodeTransformer):
    __slots__ = tuple()

    def __init__(self):
        super().__init__()

    def visit_Expr(self, node: ast.Expr):
        match node.value:
            case ast.Constant(value, kind):
                return None
        return self.generic_visit(node)
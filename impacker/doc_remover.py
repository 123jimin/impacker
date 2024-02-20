import ast

class DocRemover(ast.NodeTransformer):
    def remove_docstring(self, node):
        # TODO
        return node
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        node = self.generic_visit(node)
        return self.remove_docstring(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        node = self.generic_visit(node)
        return self.remove_docstring(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        node = self.generic_visit(node)
        return self.remove_docstring(node)
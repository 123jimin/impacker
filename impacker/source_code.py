import ast
from pathlib import Path

class SourceCode():
    """ Represents a source code file, with its (immediate) dependencies loaded. """

    file_path: Path
    root_ast: ast.Module

    local_defines: dict[str, ast.ClassDef|ast.FunctionDef|ast.AsyncFunctionDef]
    """ Dict of locally-defined class/functions. """

    import_star: set[str]
    """ Set of libraries that were imported with '*'. """

    import_lookup: dict[str, str]
    """ Dict of fully-qualified names for identifiers. """

    def __init__(self, file_path:Path, encoding:str='utf-8'):
        self.file_path = file_path
        
        self.local_defines = dict()
        self.import_star = set()
        self.import_lookup = dict()

        with open(file_path, 'r', encoding=encoding) as f:
            src = f.read()
            self.root_ast = ast.parse(src, file_path, type_comments=True)

        SourceCodeInitializer(self).visit(self.root_ast)

    def add_def(self, name:str, ast:ast.ClassDef|ast.FunctionDef|ast.AsyncFunctionDef):
        self.local_defines[name] = ast

    def add_import(self, alias:ast.alias):
        pass

    def add_import_from(self, module:str|None, level:int, alias:ast.alias):
        if module is None: module = ''
        if alias.name == '*':
            pass
        elif not module:
            pass
        else:
            pass

    def resolve(self, ident:str):
        """ Get the fully-qualified name (including the module name) of the identifier. """
        if not ident: return ident
        if ident in self.local_defines: return ident
        if fqn := self.import_lookup.get(ident): return fqn
        return ident

    def __str__(self):
        return f'<SourceCode "{self.file_path}">'

class SourceCodeInitializer(ast.NodeVisitor):
    __slots__ = ('src',)
    src: SourceCode
    
    def __init__(self, src: SourceCode):
        super().__init__()
        self.src = src
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.src.add_import(alias)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.src.add_import_from(node.module, node.level, alias)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.src.add_def(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.src.add_def(node)
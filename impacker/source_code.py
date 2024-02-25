import ast
from contextlib import contextmanager
from pathlib import Path
from importlib.machinery import ModuleSpec
from importlib.util import spec_from_file_location

from .import_group import ImportGroup

class SourceCode():
    """ Represents a source code file, with its (immediate) dependencies loaded. """

    spec: ModuleSpec
    name: str

    root_ast: ast.Module

    global_defines: dict[str, ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef]
    """ id |-> AST defining it. """

    imports: ImportGroup

    unresolved_globals: set[str]
    """ The set of variables that must be imported from an external package. """

    dependency: dict[str, set[str]]
    """
        id |-> list of variables dependent on it.
        If an unresolved global occurs outside of a definition, then the key will be an empty string.
    """

    def __init__(self, spec: ModuleSpec, encoding:str='utf-8'):
        self.spec = spec
        if not self.spec.submodule_search_locations:
            self.spec.submodule_search_locations = [str(Path(self.spec.origin).parent)]

        self.name = Path(self.spec.origin).name

        self.global_defines = dict()
        self.imports = ImportGroup()
        self.unresolved_globals = set()
        self.dependency = dict()

        with open(self.spec.origin, 'r', encoding=encoding) as f:
            src = f.read()
            self.root_ast = ast.parse(src, self.spec.origin, type_comments=True)
        
        reader = SourceCodeReader(self)
        reader.visit(self.root_ast)

    def __str__(self): return f"<SourceCode {repr(self.spec.origin)}>"
    def __repr__(self): return f"SourceCode({repr(self.spec)})"

    def add_global_define(self, def_ast: ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef):
        self.global_defines[def_ast.name] = def_ast
    
    def add_import(self, ast: ast.Import|ast.ImportFrom):
        self.imports.add(ast)
    
    @staticmethod
    def from_path(src_path: Path):
        spec = spec_from_file_location(src_path.stem, src_path)
        return SourceCode(spec) if spec else None

class SourceCodeReader(ast.NodeVisitor):
    """
        Initializes a `SourceCode` object. In specific:
        - Finds all import statements from the code.
        - Finds which undefined global variables are being referenced.

        Note: variables introduced by match-cases are currently not correctly handled.
    """

    __slots__ = ('src', 'defined_stack')
    src: SourceCode
    defined_stack: list[set[str]]
    curr_top_def_name: str

    def __init__(self, src: SourceCode):
        super().__init__()
        self.src = src
        self.defined_stack = [set()]
        self.curr_top_def_name = ""
    
    def is_defined(self, var_name: str) -> bool:
        for defs in reversed(self.defined_stack):
            if var_name in defs: return True
        return False
    
    def add_define(self, def_ast: ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef):
        self.defined_stack[-1].add(def_ast.name)
        if len(self.defined_stack) == 1:
            self.src.add_global_define(def_ast)
    
    def add_args(self, args_ast: ast.arguments):
        defs = self.defined_stack[-1]
        defs.update(arg.arg for arg in args_ast.posonlyargs)
        defs.update(arg.arg for arg in args_ast.args)
        defs.update(arg.arg for arg in args_ast.kwonlyargs)

        if args_ast.vararg:
            defs.add(args_ast.vararg.arg)

        if args_ast.kwarg:
            defs.add(args_ast.kwarg.arg)
    
    def add_name_read(self, name:str):
        # Recursion
        if name == self.curr_top_def_name: return

        for i in reversed(range(len(self.defined_stack))):
            if not i:
                # `self.curr_top_def_name` either needs an unresolved global, or another top-level definition.
                dep = self.src.dependency.get(self.curr_top_def_name)
                if dep is None:
                    dep = set()
                    self.src.dependency[self.curr_top_def_name] = dep
                dep.add(name)
            if name in self.defined_stack[i]:
                return
        
        self.src.unresolved_globals.add(name)
    
    @contextmanager
    def handle_visit_scope(self, node: ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef|ast.Lambda):
        match node:
            case ast.Lambda(): pass
            case _:
                self.add_define(node)
        
                if len(self.defined_stack) == 1:
                    self.curr_top_def_name = node.name

        self.defined_stack.append(set())

        match node:
            case ast.ClassDef(): pass
            case _: self.add_args(node.args)

        super().generic_visit(node)

        self.defined_stack.pop()
        if len(self.defined_stack) == 1:
            self.curr_top_def_name = ""

    def visit_Import(self, node: ast.Import):
        self.src.add_import(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.src.add_import(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.handle_visit_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.handle_visit_scope(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        self.handle_visit_scope(node)
    
    def visit_Lambda(self, node: ast.Lambda):
        self.handle_visit_scope(node)

    def visit_Name(self, node: ast.Name):
        match node.ctx:
            case ast.Store():
                self.defined_stack[-1].add(node.id)
            case ast.Load():
                self.add_name_read(node.id)

    def visit_Attribute(self, node: ast.Attribute):
        segments = []
        go_deeper = True
        while go_deeper:
            segments.append(node.attr)
            match node.value:
                case ast.Name(val_id):
                    segments.append(val_id)
                    go_deeper = False
                case ast.Attribute:
                    node = node.value
                case _:
                    super().generic_visit(node.value)
                    return
        assert(len(segments) > 1)
        self.add_name_read(segments[-1])
import ast
from pathlib import Path
from importlib.machinery import ModuleSpec
from importlib.util import spec_from_file_location

from .import_group import ImportGroup
from .import_resolve import find_spec_from

class SourceCode():
    """ Represents a source code file, with its (immediate) dependencies loaded. """

    spec: ModuleSpec

    root_ast: ast.Module

    global_defines: dict[str, ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef]
    """ id |-> list of defined IDs """

    imports: ImportGroup

    unresolved_globals: set[str]
    """ List of identifiers (including ones with attributes such as x.y.z) that should have been imported """

    def __init__(self, spec: ModuleSpec, encoding:str='utf-8'):
        self.spec = spec
        if not self.spec.submodule_search_locations:
            self.spec.submodule_search_locations = [str(Path(self.spec.origin).parent)]

        self.global_defines = dict()
        self.imports = ImportGroup()
        self.unresolved_globals = set()

        with open(self.spec.origin, 'r', encoding=encoding) as f:
            src = f.read()
            self.root_ast = ast.parse(src, self.spec.origin, type_comments=True)
        
        reader = SourceCodeReader(self)
        reader.visit(self.root_ast)

    def __str__(self):
        return f'<SourceCode {self.spec}>'

    def add_global_define(self, def_ast: ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef):
        self.global_defines[def_ast.name] = def_ast
    
    def add_import(self, ast: ast.Import|ast.ImportFrom):
        self.imports.add(ast)
    
    def find_spec(self, module_name:str) -> ModuleSpec|None:
        return find_spec_from(module_name, self.spec)
    
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

    def __init__(self, src: SourceCode):
        super().__init__()
        self.src = src
        self.defined_stack = [set()]
    
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

    def visit_Import(self, node: ast.Import):
        self.src.add_import(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.src.add_import(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.add_define(node)
        self.defined_stack.append(set())
        self.add_args(node.args)
        super().generic_visit(node)
        self.defined_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.add_define(node)
        self.defined_stack.append(set())
        self.add_args(node.args)
        super().generic_visit(node)
        self.defined_stack.pop()
    
    def visit_ClassDef(self, node: ast.ClassDef):
        self.add_define(node)
        self.defined_stack.append(set())
        super().generic_visit(node)
        self.defined_stack.pop()
    
    def visit_Lambda(self, node: ast.Lambda):
        self.defined_stack.append(set())
        self.add_args(node.args)
        super().generic_visit(node)
        self.defined_stack.pop()

    def visit_Name(self, node: ast.Name):
        match node.ctx:
            case ast.Store():
                self.defined_stack[-1].add(node.id)
            case ast.Load():
                if not self.is_defined(node.id):
                    self.src.unresolved_globals.add(node.id)

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
        segments = segments[::-1]
        if not self.is_defined(segments[0]):
            self.src.unresolved_globals.add(".".join(segments))
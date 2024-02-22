import ast
from pathlib import Path

class SourceCode():
    """ Represents a source code file, with its (immediate) dependencies loaded. """

    file_path: Path
    root_ast: ast.Module

    global_defines: dict[str, ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef]
    """ id |-> list of defined IDs """

    import_star: set[str]
    """ Set of packages that were imported using `import * from pkg` """

    import_alias: dict[str, str]
    """ alias_name |-> name of package that was imported with that alias; `import pkg as pkg2` """

    import_var: dict[str, str]
    """ var_name |-> name of package that imported the variable + name of the variable; `from pkg import foo as foo2` """

    unresolved_globals: set[str]
    """ List of identifiers (including ones with attributes such as x.y.z) that should have been imported """

    def __init__(self, file_path:Path, encoding:str='utf-8'):
        self.file_path = file_path

        self.global_defines = dict()
        self.import_star = set()
        self.import_alias = dict()
        self.import_var = dict()
        self.unresolved_globals = set()

        with open(file_path, 'r', encoding=encoding) as f:
            src = f.read()
            self.root_ast = ast.parse(src, file_path, type_comments=True)
        
        reader = SourceCodeReader(self)
        reader.visit(self.root_ast)

    def __str__(self):
        return f'<SourceCode "{self.file_path}">'
    
    def add_global_define(self, def_ast: ast.FunctionDef|ast.AsyncFunctionDef|ast.ClassDef):
        self.global_defines[def_ast.name] = def_ast
    
    def add_import(self, alias: ast.alias):
        self.import_alias[alias.asname or alias.name] = alias.name

    def add_import_from(self, module_name: str, alias: ast.alias):
        if alias.name == '*':
            self.import_star.add(module_name)
        else:
            self.import_var[alias.asname or alias.name] = f"{module_name}.{alias.name}"

class SourceCodeReader(ast.NodeVisitor):
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
        for alias in node.names:
            self.src.add_import(alias)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.src.add_import_from((node.level * ".") + (node.module or ""), alias)

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
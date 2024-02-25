import ast
from dataclasses import dataclass
from pathlib import Path
from importlib.machinery import ModuleSpec

from .import_group import ImportGroup, ImportModule, ImportStarFromModule, ImportFromModule
from .source_code import SourceCode

@dataclass(frozen=True, slots=True)
class CodeChunk:
    comment: str
    chunk: list[ast.stmt]

    def to_code(self, comment=True) -> str:
        code = "\n".join(map(ast.unparse, self.chunk))
        if comment and self.comment:
            code = "\n".join(f"# {line}" for line in self.comment.split("\n")) + "\n" + code
        return code

    def __str__(self) -> str:
        return self.to_code()

class Impacker:
    """ Packs a code and its dependencies into a single file. """

    verbose: bool

    compress_lib: bool
    shake_tree: bool

    _source_code_cache: dict[Path, SourceCode]

    _source_code_exports: dict[int, set[str]]
    """ id(code) |-> set of variables the source code exports """
    
    _source_code_requires: dict[int, set[str]]
    """ id(code) |-> set of variables that should be include (because they are referenced by main code) """

    def __init__(self, *, verbose=False, compress_lib=False, shake_tree=True):
        self.verbose = verbose

        self.compress_lib = compress_lib
        self.shake_tree = shake_tree
        
        self._source_code_cache = dict()
        self._source_code_exports = dict()
        self._source_code_requires = dict()

    def pack(self, in_code: SourceCode) -> str:
        self._put_source_code(in_code)
        if self.shake_tree:
            self._populate_source_code_exports(in_code)
            self._gather_source_code_requires_from_imports(in_code, in_code.unresolved_globals.copy())
            chunks = []
        else:
            chunks, import_group = self._pack_all(in_code)
            import_header = ""
            if import_group:
                import_header = "\n".join(map(ast.unparse, import_group.to_asts())) + "\n\n"
                
            return import_header + "\n\n".join(chunk.to_code() for chunk in chunks)

    def _pack_all(self, code: SourceCode) -> tuple[list[CodeChunk], ImportGroup]:
        """ Packing for `shake_tree == False`. """
        self.log(f"- Packing {code}...")
        
        chunks: list[CodeChunk] = list()

        import_group = ImportGroup()
        for imp in code.imports.ordered_imports:
            match imp:
                case ImportModule():
                    import_group.add(imp)
                case _:
                    if spec := code.find_spec(imp.module):
                        if not self.has_source_code(spec):
                            src = self.get_source_code(spec)
                            module_chunks, module_import_group = self._pack_all(src)

                            chunks.extend(module_chunks)
                            import_group.extend(module_import_group)
                    else:
                        print('unresolved', code.spec, imp.module)
                        import_group.add(imp)

        stmts: list[ast.stmt] = []
        for stmt in code.root_ast.body:
            match stmt:
                case ast.Import(_):
                    pass
                case ast.ImportFrom(_, names):
                    for alias in names:
                        if alias.asname:
                            stmts.append(ast.Assign([ast.Name(alias.asname, ast.Store())], ast.Name(alias.name, ast.Load())))
                case _:
                    stmts.append(stmt)
        
        if stmts:
            chunks.append(CodeChunk(f"From {code.name}", [ast.fix_missing_locations(stmt) for stmt in stmts]))

        return (chunks, import_group)

    def _populate_source_code_exports(self, code: SourceCode) -> set[str]:
        code_id = id(code)
        if code_id in self._source_code_exports: return {}
        
        self.log(f"- Populating source_code_exports[{code}]...")

        exports = set[str]()
        self._source_code_exports[code_id] = exports

        for imp in code.imports:
            match imp:
                case ImportModule(_, alias):
                    pass
                case ImportStarFromModule(module):
                    if spec := code.find_spec(module):
                        exports.add(self._populate_source_code_exports(self.get_source_code(spec)))
                case ImportFromModule(_, _, alias):
                    exports.add(alias)

        exports.update(code.global_defines.keys())
        return exports

    def _mark_source_code_requires(self, code: SourceCode, requires: set[str]):
        """ Given that `requires` is needed from `code`, mark all definitions from `code` that's needed. """
        if not requires: return

        self._gather_source_code_requires_from_imports(code, requires)
    
    def _gather_source_code_requires_from_imports(self, code: SourceCode, requires: set[str]):
        """ Given that `requires` is needed, lookup imported  """
        pass

    def get_source_code(self, spec: ModuleSpec) -> SourceCode:
        code_path = spec.origin

        if code := self._source_code_cache.get(code_path):
            return code

        code = SourceCode(spec)
        self._put_source_code(code)
        return code

    def has_source_code(self, spec: ModuleSpec) -> bool:
        return spec.origin in self._source_code_cache

    def _put_source_code(self, code: SourceCode):
        self._source_code_cache[code.spec.origin] = code
        self._source_code_requires[id(code)] = set()

    def log(self, *args):
        if self.verbose: print(*args)
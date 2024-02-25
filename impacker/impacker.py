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

    _source_code_import_cache: dict[int, dict[str, SourceCode|None]]
    """ id(code) |-> module |-> get_source_code(code.find_spec(module))"""
    
    _source_code_requires: dict[int, set[str]]
    """ id(code) |-> set of variables that should be include (because they are referenced by main code) """

    _source_code_externals: set[int, set[str]]
    """ id(code) |-> set of variables that were already inspected for external package usage """

    def __init__(self, *, verbose=False, compress_lib=False, shake_tree=True):
        self.verbose = verbose

        self.compress_lib = compress_lib
        self.shake_tree = shake_tree
        
        self._source_code_cache = dict()
        self._source_code_import_cache = dict()
        self._source_code_requires = dict()
        self._source_code_externals = dict()

    def pack(self, in_code: SourceCode) -> str:
        self._put_source_code(in_code)

        if self.shake_tree:
            self.log("Marking which definitions should be exported...")
            self._gather_source_code_requires_from_imports(in_code, in_code.unresolved_globals.copy())
   
        self.log("Packing source codes...")

        chunks, import_group = self._pack_from(in_code, set())
        import_header = ""
        if import_group:
            import_header = "\n".join(map(ast.unparse, import_group.to_asts())) + "\n\n"
            
        return import_header + "\n\n".join(chunk.to_code() for chunk in chunks)

    def _pack_from(self, code: SourceCode, visited: set[int]) -> tuple[list[CodeChunk], ImportGroup]:
        self.log(f"- Packing {code}...")
        is_root = (len(visited) == 0)
        visited.add(id(code))
        
        chunks: list[CodeChunk] = list()

        import_group = ImportGroup()
        for imp in code.imports.ordered_imports:
            match imp:
                case ImportModule():
                    import_group.add(imp)
                case _:
                    if imp_code := self.get_import(code, imp.module):
                        if id(imp_code) not in visited:
                            module_chunks, module_import_group = self._pack_from(imp_code, visited)

                            chunks.extend(module_chunks)
                            import_group.extend(module_import_group)
                    else:
                        import_group.add(imp)

        stmts: list[ast.stmt] = []
        requires = self._source_code_requires.get(id(code))

        if is_root or (requires is None):
            # Pack everything from this source code.
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
        elif requires:
            # Pack only what's required
            for req in requires:
                assert req in code.global_defines
                stmts.append(code.global_defines[req])
        
        if stmts:
            chunks.append(CodeChunk(f"From {code.name}", [ast.fix_missing_locations(stmt) for stmt in stmts]))

        return (chunks, import_group)

    def _mark_source_code_requires(self, code: SourceCode, requires: set[str]):
        """ Given that `requires` is needed from `code`, mark all definitions from `code` that's needed. """
        if not requires: return

        self.log(f"- Inspecting {code} for {repr(requires)}...")

        code_id = id(code)
        req_set = self._source_code_requires[code_id]
        if req_set is None:
            req_set = set[str]()
            self._source_code_requires[code_id] = req_set

        externals = set()

        while requires:
            next_requires = set()

            for req in requires:
                if req in req_set:
                    continue
                if req in externals:
                    continue
                if req in code.global_defines:
                    req_set.add(req)
                    if next_reqs := code.dependency.get(req):
                        next_requires.update(next_reqs)
                else:
                    externals.add(req)
            
            requires = next_requires
        
        prev_externals = self._source_code_externals.get(code_id)
        if prev_externals is None:
            prev_externals = set()
            self._source_code_externals[code_id] = prev_externals
        
        externals -= prev_externals
        prev_externals |= externals

        self._gather_source_code_requires_from_imports(code, externals)
    
    def _gather_source_code_requires_from_imports(self, code: SourceCode, requires: set[str]):
        """ Given that `requires` is needed, lookup imports to mark required definitions. """
        for imp in reversed(code.imports.ordered_imports):
            if not requires: return
            match imp:
                case ImportModule(_, alias):
                    pass
                case ImportStarFromModule(module):
                    if imp_code := self.get_import(code, module):
                        self._mark_source_code_requires(imp_code, requires)
                case ImportFromModule(module, name, alias):
                    if imp_code := self.get_import(code, module):
                        if alias in requires:
                            requires.remove(alias)
                            self._mark_source_code_requires(imp_code, {name})

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

    def get_import(self, code: SourceCode, module: str) -> SourceCode|None:
        code_id = id(code)
        import_map = self._source_code_import_cache.get(code_id)
        if import_map is None:
            import_map = dict[str, SourceCode|None]()
            self._source_code_import_cache[code_id] = import_map
        
        if module in import_map:
            return import_map[module]
        
        spec = code.find_spec(module)
        ret = self.get_source_code(spec) if spec else None
        
        import_map[module] = ret
        return ret

    def log(self, *args):
        if self.verbose: print(*args)
import ast
from dataclasses import dataclass
from pathlib import Path
from importlib.machinery import ModuleSpec

from .docstring_remover import DocstringRemover
from .import_group import ImportGroup, ImportModule, ImportStarFromModule, ImportFromModule
from . import import_resolve
from .source_code import SourceCode

@dataclass(frozen=True, slots=True)
class CodeChunk:
    """ Represents a chunk of code, with optional comment attached. """

    comment: str
    chunk: list[ast.stmt]

    def to_code(self, comment=True) -> str:
        """ Unparse the chunk into code. Set `comment=False` to omit the comment. """
        code = "\n".join(map(ast.unparse, self.chunk))
        if comment and self.comment:
            code = "\n".join(f"# {line}" for line in self.comment.split("\n")) + "\n" + code
        return code
    
    def apply_transform(self, transformer: ast.NodeTransformer|None):
        """ Apply `transformer` to each statement in this chunk. """
        if not transformer: return
        for i, stmt in enumerate(self.chunk):
            self.chunk[i] = transformer.visit(stmt)

    def __str__(self) -> str:
        """ Unparse the chunk into code, with comments attached. """
        return self.to_code()

class Impacker:
    """ Packs a code and its dependencies into a single file. """

    verbose: bool
    """ Whether to print verbose log. """

    shake_tree: bool
    """ Whether to remove unused imports. """

    inline: bool
    """ Whether to inline functions decorated with `@inline`. """

    include_source_location: bool
    """ Whether to include source location comments. """

    strip_docstring: bool
    """ Whether to strip docstrings. """

    _source_code_cache: dict[Path, SourceCode]

    _source_code_import_cache: dict[int, dict[str, SourceCode|None]]
    """ id(code) |-> module |-> get_source_code(code.find_spec(module))"""
    
    _source_code_requires: dict[int, set[str]]
    """ id(code) |-> set of variables that should be included (because they are referenced by main code) """

    _source_code_externals: dict[int, set[str]]
    """ id(code) |-> set of variables that should be imported for this code """

    def __init__(self, *, verbose=False, shake_tree=True, inline=True, strip=False, include_source_location=True, strip_docstring=False):
        self.verbose = verbose

        self.shake_tree = shake_tree

        self.strip_docstring = strip_docstring or strip
        self.include_source_location = include_source_location and not strip

        self._source_code_cache = dict()
        self._source_code_import_cache = dict()
        self._source_code_requires = dict()
        self._source_code_externals = dict()

    def pack(self, in_code: SourceCode) -> str:
        """ Pack the given source code into a single string. """

        self.log(f"Packing {in_code}...")
        self.log(f"- Using sys.path = {repr(import_resolve.sys_path)}")

        self._put_source_code(in_code)
        self._source_code_externals[id(in_code)] = in_code.unresolved_globals.copy()

        if self.shake_tree:
            self.log("Marking which definitions should be exported...")
            self._gather_source_code_requires_from_imports(in_code, in_code.unresolved_globals.copy())
   
        self.log("Packing source codes...")

        chunks, import_group = self._pack_from(in_code, set())
        import_header = ""
        if import_group:
            import_header = "\n".join(map(ast.unparse, import_group.to_asts()))
        
        if self.strip_docstring:
            docstring_remover = DocstringRemover()
            for chunk in chunks: chunk.apply_transform(docstring_remover)

        import_body = "\n\n".join(chunk.to_code(self.include_source_location) for chunk in chunks)

        if import_header:
            return f"{import_header}\n\n{import_body}"
        else:
            return import_body

    def clear(self):
        """ Clear all caches. """
        self._source_code_cache.clear()
        self._source_code_import_cache.clear()
        self._source_code_requires.clear()
        self._source_code_externals.clear()

    def _pack_from(self, code: SourceCode, visited: set[int]) -> tuple[list[CodeChunk], ImportGroup]:
        self.log(f"- Packing {code}...")
        is_root = (len(visited) == 0)
        code_id = id(code)

        code_name = "main code" if is_root else code.name

        visited.add(code_id)
        
        chunks: list[CodeChunk] = list()

        externals = None
        need_externals = False

        if self.shake_tree:
            externals = self._source_code_externals.get(code_id)
            need_externals = True

        import_group = ImportGroup()
        for imp in code.imports.ordered_imports:
            match imp:
                case ImportModule(_, alias):
                    # Do not import when `alias` is not marked as something that's required.
                    if (not need_externals) or (externals and (alias in externals)):
                        import_group.add(imp)
                case _:
                    if imp_code := self.get_import(code, imp.module):
                        if id(imp_code) not in visited:
                            module_chunks, module_import_group = self._pack_from(imp_code, visited)

                            chunks.extend(module_chunks)
                            import_group.extend(module_import_group)
                    else:
                        # TODO: do not include unused `import module` or `from module import *` statements.
                        if (not need_externals) or externals:
                            import_group.add(imp)

        if is_root or not self.shake_tree:
            # Pack everything from this source code.
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
                chunks.append(CodeChunk(f"From {code_name}", [ast.fix_missing_locations(stmt) for stmt in stmts]))
        elif requires := self._source_code_requires.get(code_id):
            # Pack only what's required, in the order they appear in original source code.
            req_defs = []
            for req in requires:
                req_def = code.global_defines[req]
                req_defs.append(((req_def.lineno, req_def.col_offset), req_def))
            
            chunks.extend(CodeChunk(f"{req_def.name} | from {code_name}, line {req_def.lineno}", [req_def]) for (_, req_def) in sorted(req_defs))

        return (chunks, import_group)

    def _mark_source_code_requires(self, code: SourceCode, requires: set[str]):
        """ Given that `requires` is needed from `code`, mark all definitions from `code` that's needed. """
        if not requires: return

        self.log(f"- Inspecting {code} for {repr(requires)}...")

        code_id = id(code)
        req_set = self._source_code_requires.get(code_id)
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

        if code := self._source_code_cache.get(Path(code_path or "")):
            return code

        code = SourceCode(spec)
        self._put_source_code(code)
        return code

    def has_source_code(self, spec: ModuleSpec) -> bool:
        return spec.origin in self._source_code_cache

    def _put_source_code(self, code: SourceCode):
        self._source_code_cache[Path(code.spec.origin or "")] = code
        self._source_code_requires[id(code)] = set()

    def get_import(self, code: SourceCode, module: str) -> SourceCode|None:
        code_id = id(code)
        import_map = self._source_code_import_cache.get(code_id)
        if import_map is None:
            import_map = dict[str, SourceCode|None]()
            self._source_code_import_cache[code_id] = import_map
        
        if module in import_map:
            return import_map[module]
        
        spec = self.find_spec_from(code.spec, module)
        ret = self.get_source_code(spec) if spec else None
        
        import_map[module] = ret
        return ret

    def find_spec_from(self, spec: ModuleSpec, module: str) -> ModuleSpec|None:
        return import_resolve.find_spec_from(module, spec)

    def log(self, *args):
        if self.verbose: print(*args)
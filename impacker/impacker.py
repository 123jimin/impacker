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
    _source_code_requires: dict[int, set[str]]

    def __init__(self, *, verbose=False, compress_lib=False, shake_tree=True):
        self.verbose = verbose

        self.compress_lib = compress_lib
        self.shake_tree = shake_tree
        
        self._source_code_cache = dict()
        self._source_code_requires = dict()

    def pack(self, in_code: SourceCode) -> str:
        self.get_source_code(in_code.spec)
        if self.shake_tree:
            chunks = []
        else:
            chunks, import_group = self._pack_all(in_code)
            import_header = ""
            if import_group:
                import_header = "\n".join(map(ast.unparse, import_group.to_asts())) + "\n\n"
                
            return import_header + "\n\n".join(chunk.to_code() for chunk in chunks)

    def _pack_all(self, in_code: SourceCode) -> tuple[list[CodeChunk], ImportGroup]:
        """ Packing for `shake_tree == False`. """
        
        chunks: list[CodeChunk] = list()

        import_group = ImportGroup()
        for imp in in_code.imports.ordered_imports:
            match imp:
                case ImportModule():
                    import_group.add(imp)
                case _:
                    if spec := in_code.find_spec(imp.module):
                        if not self.has_source_code(spec):
                            src = self.get_source_code(spec)
                            module_chunks, module_import_group = self._pack_all(src)

                            chunks.extend(module_chunks)
                            import_group.extend(module_import_group)
                    else:
                        print('unresolved', in_code.spec, imp.module)
                        import_group.add(imp)

        stmts: list[ast.stmt] = []
        for stmt in in_code.root_ast.body:
            match stmt:
                case ast.Import(_): pass
                case ast.ImportFrom(_): pass
                case _: stmts.append(stmt)
        
        if stmts:
            chunks.append(CodeChunk(f"From {in_code.name}", stmts))

        return (chunks, import_group)

    def get_source_code(self, spec: ModuleSpec) -> SourceCode:
        code_path = spec.origin

        if src := self._source_code_cache.get(code_path):
            return src

        src = SourceCode(spec)
        self._source_code_cache[code_path] = src
        self._source_code_requires[id(src)] = set()
        return src

    def has_source_code(self, spec: ModuleSpec) -> bool:
        return spec.origin in self._source_code_cache

    def log(self, *args):
        if self.verbose: print(*args)
"""
    This file contains classes (most notably `ImportGroup`) for representing import statements.
"""

import ast
from dataclasses import dataclass
from typing import Self

from .import_resolve import split_module_name

@dataclass(frozen=True, slots=True)
class ImportModule():
    """ `import {module} as {alias}`, including `import {module}` (where `module == alias`) """
    module: str
    alias: str

    def to_ast(self) -> ast.Import:
        return ast.Import([ast.alias(self.module, self.alias if self.alias != self.module else None)])

@dataclass(frozen=True, slots=True)
class ImportStarFromModule():
    """ `from {module} import *` """
    module: str

    def to_ast(self) -> ast.ImportFrom:
        level, module = split_module_name(self.module)
        return ast.ImportFrom(module, [ast.alias('*', None)], level)

@dataclass(frozen=True, slots=True)
class ImportFromModule():
    """ `from {module} import {name} as {alias}` including `from {module} import {name}` (where `name == alias`) """
    module: str
    name: str
    alias: str
    
    def to_ast(self) -> ast.ImportFrom:
        level, module = split_module_name(self.module)
        return ast.ImportFrom(module, [ast.alias(self.name, self.alias if self.alias != self.name else None)], level)

class ImportGroup:
    """ A collection of multiple import statements. """

    __slots__ = ('ordered_imports',)
    ordered_imports: list[ImportModule|ImportStarFromModule|ImportFromModule]
    
    def __init__(self): self.ordered_imports = []

    def __bool__(self): return len(self.ordered_imports) > 0
    def __len__(self): return len(self.ordered_imports)
    def __iter__(self): yield from self.ordered_imports
    
    def add(self, node: ast.Import|ast.ImportFrom|ImportModule|ImportStarFromModule|ImportFromModule):
        """ Adds an import statement to the group. """
        match node:
            case ast.Import(names):
                for alias in names:
                    self.ordered_imports.append(ImportModule(alias.name, alias.asname or alias.name))
            case ast.ImportFrom(module, names, level):
                module_name = (level * ".") + (module or "")
                for alias in names:
                    if alias.name == '*':
                        self.ordered_imports.append(ImportStarFromModule(module_name))
                    else:
                        self.ordered_imports.append(ImportFromModule(module_name, alias.name, alias.asname or alias.name))
            case _:
                self.ordered_imports.append(node)

    def extend(self, other: Self):
        """ Extends the group with another group. """
        self.ordered_imports.extend(other.ordered_imports)
        return self

    def to_asts(self) -> list[ast.Import|ast.ImportFrom]:
        """ Converts the group to a list of AST nodes. """
        imports = set[tuple[str, str]]()
        import_stars = dict[str, ImportStarFromModule]()
        import_froms = dict[str, tuple[set[str], list[ast.alias]]]()
        
        for imp in self.ordered_imports:
            match imp:
                case ImportModule(module, alias):
                    imports.add((module, alias))
                case ImportStarFromModule(module):
                    import_stars[module] = imp
                case ImportFromModule(module, name, alias):
                    import_from = import_froms.get(module)
                    if import_from is None:
                        import_from = (set[str](), list[ast.alias]())
                        import_froms[module] = import_from
                    
                    s, l = import_from
                    if alias not in s:
                        s.add(alias)
                        l.append(ast.alias(name, alias if alias != name else None))
        
        import_asts = list[ast.Import|ast.ImportFrom]()

        if len(imports) > 0:
            import_asts.append(ast.Import([ast.alias(module, alias if alias != module else None) for (module, alias) in imports]))
        
        import_asts.extend(imp.to_ast() for imp in import_stars.values())

        for (module, (_, alias_list)) in import_froms.items():
            level, module = split_module_name(module)
            import_asts.append(ast.ImportFrom(module, alias_list, level))

        return import_asts
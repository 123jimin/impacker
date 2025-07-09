import sys
from pathlib import Path
from importlib.machinery import PathFinder, ModuleSpec
from importlib.util import spec_from_file_location

def is_builtin_dir(path_dir:str) -> bool:
    return any(path_dir.startswith(builtin_dir) for builtin_dir in (sys.base_prefix, sys.base_exec_prefix))

sys_path = [p for p in sys.path if p and not is_builtin_dir(p)]

def split_module_name(module:str) -> tuple[int, str]:
    """ Returns `(level, module)`, where `level` is the distance to the top-level package. """
    for level in range(len(module)):
        if module[level] != '.':
            return (level, module[level:])
    return (len(module), '')

def find_spec_from(module: str, from_spec: ModuleSpec, from_locs: list[str]|None = None) -> ModuleSpec|None:
    """
        Find the spec for the module, assuming that a Python code in `file_path` is trying to import it, and its package path is `package_path`.
    """
    level, module = split_module_name(module)

    # Handle absolute import
    if from_locs is None:
        from_locs = from_spec.submodule_search_locations
        if from_locs is not None:
            from_locs = from_locs + sys_path
    if not level:
        # Try finding the whole spec
        if spec := PathFinder.find_spec(module, from_locs):
            return spec
        
        # First, try locating the root module...
        root, _, rest = module.partition('.')
        if not rest: return None

        spec = PathFinder.find_spec(root, from_locs)
        if (spec is None) or (not rest): return spec
        
        # ... then assume that we're resolving a relative import.
        # (This is not the correct way to find submodule, but let's ignore more complex cases.)
        module = "." + rest
        from_spec = spec
        level = 1

    # Relative import
    rel_dir = Path(from_spec.origin or "")
    for _ in range(level):
        rel_dir = rel_dir.parent
    assert rel_dir.is_dir()
    if module:
        segments = module.split('.')
        for i, segment in enumerate(segments):
            if i < len(segments) - 1:
                rel_dir = rel_dir / segment
            else:
                module_path = rel_dir / f"{segment}.py"
                if module_path.is_file():
                    return spec_from_file_location(module, module_path)
                module_path = rel_dir / segment
                if module_path.is_dir():
                    module_path = module_path / "__init__.py"
                    if module_path.is_file():
                        return spec_from_file_location(module, module_path)
    else:
        init_file_path = rel_dir / "__init__.py"
        if init_file_path.is_file():
            return spec_from_file_location(module, init_file_path)
    
    return None
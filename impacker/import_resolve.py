from pathlib import Path
from importlib.machinery import PathFinder, ModuleSpec
from importlib.util import spec_from_file_location

def split_module_name(module:str) -> tuple[int, str]:
    for level in range(len(module)):
        if module[level] != '.':
            return (level, module[level:])
    return (len(module), '')

def find_spec_from(module:str, from_spec: ModuleSpec) -> ModuleSpec|None:
    """
        Find the spec for the module, assuming that a Python code in `file_path` is trying to import it, and its package path is `package_path`.
    """
    level, module = split_module_name(module)

    # Handle absolute import
    if not level: return PathFinder.find_spec(module, from_spec.submodule_search_locations)

    # Relative import
    rel_dir = Path(from_spec.origin)
    for _ in range(level):
        rel_dir = rel_dir.parent
    assert rel_dir.is_dir()
    if module:
        segments = module.split('.')
        for i, segment in enumerate(segments):
            if i < len(segment) - 1:
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
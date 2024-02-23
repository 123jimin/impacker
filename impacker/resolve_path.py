import os, sys
from pathlib import Path

# Note: it's likely that these code can be replaced by simple applications of `importlib`,
# but so far I haven't find an easy way of doing this.

def is_builtin_dir(dir_path:str) -> bool:
    return any(dir_path.startswith(base_path) for base_path in (sys.prefix, sys.exec_prefix))

def resolve_path(src_path:str, module_name:str) -> Path|None:
    """ Assuming that a source code is located under `src_path`, get the path to the module. """
    dir_path = Path(src_path).resolve().parent
    if resolved_path := resolve_path_from(dir_path, module_name):
        assert resolved_path.is_file()
        return resolved_path

    for import_path in sys.path:
        if not import_path or is_builtin_dir(import_path): continue
        if resolved_path := resolve_path_from(Path(import_path).resolve(), module_name):
            assert resolved_path.is_file()
            return resolved_path
    
    return None

def resolve_path_from(root_dir_path:Path|str, module_name:str) -> Path|None:
    """
        Given `root_dir_path`, find the file responsible for `module_name`.
        Note: this function's algorithm is likely *not* accurate...
    """
    if isinstance(root_dir_path, str):
        root_dir_path = Path(root_dir_path).resolve()
    elif not root_dir_path.is_absolute():
        root_dir_path = root_dir_path.resolve()

    if not root_dir_path.is_dir():
        return None

    level = 0
    while level < len(module_name) and module_name[level] == '.':
        if level:
            root_dir_path = root_dir_path.parent
            if not root_dir_path.is_dir():
                return None
        level += 1
    
    assert root_dir_path.is_dir()
    
    module_name = module_name[level:]
    if not module_name:
        module_path = root_dir_path / "__init__.py"
        if module_path.is_file():
            return module_path
        else:
            return None
    
    module_dir_path = root_dir_path
    module_parts = module_name.split(".")
    for (i, module_part) in enumerate(module_parts):
        if i < len(module_parts) - 1:
            # Traverse directory
            module_dir_path = module_dir_path / module_part
            if not module_dir_path.is_dir():
                return None
        else:
            # Check whether the module exists
            module_path = module_dir_path / module_part
            if module_path.is_dir():
                module_path = module_path / "__init__.py"
                if module_path.is_file():
                    return module_path
            module_path = module_dir_path / f"{module_part}.py"
            if module_path.is_file():
                return module_path
            return None
    assert False


import unittest
class ResolvePathTester(unittest.TestCase):
    """ Temporary test for developing """

    test_dir = Path(__file__).parent.parent / "test"
    def test(self):
        test_data = [
            ('foo', "foo/__init__.py"),
            ('bar', "bar/__init__.py"),
            ('foo.x', "foo/x.py"),
        ]

        for (module_name, expected) in test_data:
            actual = resolve_path_from(self.test_dir, module_name)
            if expected:
                self.assertEqual(actual.relative_to(self.test_dir).as_posix(), expected, f"resolve_path_from for {module_name=} returned {actual}")
            else:
                self.assertIsNone(actual, f"resolve_path_from for {module_name=}")

if __name__ == '__main__':
    unittest.main()
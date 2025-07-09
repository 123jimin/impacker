import ast, unittest

from .util import load_example_code

class TestSourceCode(unittest.TestCase):
    def test_t01(self):
        source_code = load_example_code("t01")
        self.assertEqual(source_code.name, "t01.py")

        self.assertIsInstance(source_code.root_ast, ast.Module)
        
        # Check that there are no imports.
        imports = source_code.imports
        self.assertFalse(imports)
        self.assertEqual(len(imports), 0)
        self.assertListEqual(list(imports), [])

        # Check that there is no global definition.
        self.assertFalse(source_code.global_defines)
        
        # Check that there is one unresolved dependency: the `print` function.
        self.assertListEqual(list(source_code.unresolved_globals), ['print'])
        self.assertEqual(len(source_code.dependency), 1)
        self.assertListEqual(list(next(iter(source_code.dependency.values()))), ['print'])
    
    def test_t02(self):
        source_code = load_example_code("t02")
        self.assertEqual(source_code.name, "t02.py")

        self.assertIsInstance(source_code.root_ast, ast.Module)

        # Check that 
import ast
from pathlib import Path

class SourceCode():
    """ Represents a source code file, with its (immediate) dependencies loaded. """

    file_path: Path
    root_ast: ast.Module

    def __init__(self, file_path:Path, encoding:str='utf-8'):
        self.file_path = file_path

        with open(file_path, 'r', encoding=encoding) as f:
            src = f.read()
            self.root_ast = ast.parse(src, file_path, type_comments=True)

    def __str__(self):
        return f'<SourceCode "{self.file_path}">'
from pathlib import Path
from impacker import SourceCode

EXAMPLE_DIR = Path(__file__).parent.parent / "example"

def load_example_code(file_name: str) -> SourceCode:
    if not file_name.endswith(".py"): file_name += ".py"
    
    code = SourceCode.from_path(EXAMPLE_DIR / file_name)
    assert code is not None, f"Failed to load example source code '{file_name}'!"

    return code
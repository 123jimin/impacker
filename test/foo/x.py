import math

def foo_util(id:str) -> str:
    return f"foo_{id}_{math.sqrt(len(id))}"

def foo_x() -> str:
    return foo_util("x")
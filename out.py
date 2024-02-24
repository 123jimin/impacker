import math

# From x
def foo_util(id: str) -> str:
    return f'foo_{id}_{math.sqrt(len(id))}'
def foo_x() -> str:
    return foo_util('x')

# From y
def foo_y() -> str:
    return foo_util('y')

# From x
def bar_x() -> str:
    return f'bar_x (not {foo_x()})'

# From code
def foo():

    def bar():
        return 123
    x, z = (1, 3)
    x += (y := 123)
    return 42 + bar()
print(bar_x(), foo_y(), sep=', ')
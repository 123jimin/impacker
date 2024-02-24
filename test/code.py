from foo import foo_y
from bar import bar_x

def foo():
    def bar():
        return 123
    x, z = 1, 3
    x += (y := 123)
    return 42 + bar()

print(bar_x(), foo_y(), sep=", ")
from foo import foo_y
import bar

def foo():
    def bar():
        return 123
    x, z = 1, 3
    x += (y := 123)
    return 42 + bar()

print(bar.bar_x(), foo_y(), sep=", ")
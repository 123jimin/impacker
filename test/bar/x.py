from foo.x import foo_x

def bar_x() -> str:
    return f"bar_x (not {foo_x()})"
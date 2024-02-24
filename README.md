# impacker

`impacker` is a simple Python utility for packing all dependencies of a Python code into the same file, removing dependency.

The primary purpose of this tool is to prepare Python code for submission to online judge systems, where multiple files are often not supported.

`impacker`는 파이썬 코드가 참조하는 모든 라이브러리 코드를 단일 파일로 패킹하여, 코드의 의존성을 제거하는 간단한 유틸리티 프로그램입니다.

하나의 소스 코드 파일을 제출해야 하는 온라인 저지 시스템에서 파이썬 코드를 제출하고 싶을 때 유용합니다.

**NOTE: this project is currently work-in-progress. 이 프로젝트는 현재 개발중입니다.**

## Features

- Merges a Python code and its dependencies into a single file.
- Performs tree shaking; unused codes are not included.
- Leaves or strips comments and docstrings.
- Compresses large source code.

## Limitations

- It recognizes from-import statements such as `from x import y as z` and `from x import *`, but not `import x`.
  - This also applies to all indirect dependencies.
- Only class and function definitions from other modules will be imported.
  - In other words, modules with side-effects are not allowed.
- It may not work correctly when an import statement is not in a top-level code.
- It may not work correctly when match-case statements are used, but they should not cause a problem in most cases.

## Usage

Consider the case where there is a library `foo.py`, and a code `main.py` using it.

```py
# foo.py

class FooClass:
    def __init__(self, x):
        self.x = x

def print_foo(foo):
    print("foo", foo.x)

def something_else():
    print("something else")
```

```py
# main.py
from foo import FooClass, print_foo

foo = FooClass(42)
print_foo(foo)
```

impacker can be used like this:

```text
impacker main.py out.py
```

A new file `out.py` will be generated.

```py
# out.py

class FooClass:
    def __init__(self, x):
        self.x = x

def print_foo(foo):
    print("foo", foo.x)

foo = FooClass(42)
print_foo(foo)

```
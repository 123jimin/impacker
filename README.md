# impacker

- [한국어](README.ko-KR.md)

`impacker` is a simple Python utility for packing all dependencies of a Python code into the same file, removing dependency.

This tool was created to create submissions to online judge systems for competitive programming, where submitting multiple files are rarely (if not never at all) supported.
In specific, the competitive programming library for Python, [ckp](https://github.com/123jimin/ckp), was created with impacker in mind, and vice-versa.

## Features

- Merges a Python code and its dependencies into a single file.
- Performs tree shaking; unused codes are not included.
- (Planned) Leaves or strips comments and docstrings.
- (Planned) Compresses large source code.

## Example

This code checks whether a given number is a prime number, using `ckp`.

```py
from ckp.number_theory import is_prime_naive

N = int(input())
print(is_prime_naive(N))
```

This code can't be run independently; `ckp` must be installed to run this file.

Assuming that the code's filename is `code.py`, and you wish the result file's name to be `out.py`, impacker can be run like the following:

```sh
poetry run python -m impacker code.py out.py
```

`out.py` will contain the packed source code, which can be run without `ckp`.

```py
import math

# From primality_test.py
def is_prime_naive(n: int) -> bool:
    """
        Naive primality testing.
        - Time: `O(sqrt(n))`
    """
    if n < 100:
        return n in {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97}
    if n % 2 == 0 or n % 3 == 0 or n % 5 == 0 or (n % 7 == 0) or (n % 11 == 0):
        return False
    for p in range(13, math.isqrt(n) + 1, 6):
        if n % p == 0 or n % (p + 4) == 0:
            return False
    return True

# From test.py
N = int(input())
print(is_prime_naive(N))
```

## Limitations

While impacker could be used on packages other than `ckp`, it's primarily to be used together with `ckp`, and packages other than `ckp` might not be supported very well.

In specific, impacker currently has following limitations.

- `import` statements importing the whole module (such as `import x`, or `from x import y` where `x.y` is a module) will be left as-is.
  - Use import statements such as `from x import y`, `from x import y or z`, or `from x import *` to properly use impacker.
  - Any form of `import` is fine when you don't want the module to be merged (such as built-in modules like `math`, `collections`, etc...).
- When tree-shaking is enabled, only the definitions for classes and functions will be merged.
  - In other words, modules with side-effects or global variables may not work correctly.
- When the import statement is being used inside a block (such as if-else statements or functions), it may not work correctly.

## How to Use

I *strongly* recommend using [Poetry](https://python-poetry.org/) for managing Python dependencies.
(Still, impacker can be used without Poetry.)

```sh
poetry add git+https://github.com/123jimin/impacker.git
poetry run python -m impacker -h
```

```text
usage: impacker [-h] [-c] [-v] [--no-shake-tree] IN_FILE OUT_FILE

Merge a Python code and its dependencies into a single file.     

positional arguments:
  IN_FILE             code file to pack
  OUT_FILE            name of file to generate

options:
  -h, --help          show this help message and exit
  -c, --compress-lib  compress packed library codes
  -v, --verbose       prints verbose log
  --no-shake-tree     do not shake import tree
```

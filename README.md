# impacker

- [한국어](README.ko-KR.md)

`impacker` is a simple Python utility for packing all dependencies of a Python code into the same file, removing dependency.

The primary purpose of this tool is to prepare Python code for submission to online judge systems, where multiple files are often not supported.

## Features

> [!CAUTION]
> Most features are currently work-in-progress.

List of features:

- Merges a Python code and its dependencies into a single file.
- Performs tree shaking; unused codes are not included.
- Leaves or strips comments and docstrings.
- Compresses large source code.

## Limitations

- Packages import via `import x` will *not* be merged.
  - Use something like `from x import y`, `from x import y or z`, or `from x import *`.
- When tree-shaking is enabled, only the definitions for classes and functions will be merged.
  - In other words, modules with side-effects or global variables may not work correctly.
- When the import statement is being used inside a block (such as if-else statements or functions), it may not work correctly.
- Using match-case statements may cause the tool to work incorrectly. Still, for most cases it should work well.

## How to Use

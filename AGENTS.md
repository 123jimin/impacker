# Project Guidelines for Automated Agents

This `AGENTS.md` provides comprehensive guidance on navigating and contributing to this codebase, for both human developers and automated agents (such as OpenAI Codex).

## Overview

`impacker` is a Python CLI tool that merges Python source files and their dependencies into a single script.
It is mainly used to generate standalone submission files for online judge systems.

```
> python -m impacker -h

usage: impacker [-h] [-v] [--no-shake-tree] [--no-inline] [-s] [--strip-docstring] [--no-include-source-location] IN_FILE OUT_FILE

Merge a Python code and its dependencies into a single file.

positional arguments:
  IN_FILE               code file to pack
  OUT_FILE              name of file to generate

options:
  -h, --help            show this help message and exit
  -v, --verbose         prints verbose log
  --no-shake-tree       do not shake import tree
  --no-inline           do not inline functions decorated with `@inline`
  -s, --strip           strip all comments and docstrings
  --strip-docstring     strip all docstrings
  --no-include-source-location
                        omit source code location comments
```

This project uses Poetry for dependency management and packaging.

## Directory Structure

- `/impacker`: Code for the main package.
  - `/impacker/cli`
  - `/impacker/core`
- `/test`: Code for testing.
  - `/test/example`: Example codes for testing.
    - `t00.py`, `t01.py`, ... are example codes to run tests on.
    - `l01`, `l02`, ... are libraries that the example codes import.
    - `README.md` describes what are being tested in each example code.

## Program Structure

(TODO)

## Guidelines

- Target Python version is 3.13.
- Use type hints where possible.
- Keep the project lightweight, and avoid introducing large external dependencies.
- Run the tests with `python -m test`, before submitting changes.
- Soft limit for line length is 120 characters.
- Document public classes and functions with docstrings.
- Write clear commit messages and keep the commit history tidy.
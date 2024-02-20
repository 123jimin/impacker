# impacker

`impacker` is a simple Python utility for packing all dependencies of a Python code into the same file, removing dependency.

The primary purpose of this tool is to prepare Python code for submission to online judge systems, where multiple files are often not supported.

`impacker`는 파이썬 코드가 참조하는 모든 라이브러리 코드를 단일 파일로 패킹하여, 코드의 의존성을 제거하는 간단한 유틸리티 프로그램입니다.

이 도구는 하나의 소스 코드 파일을 제출해야 하는 온라인 저지 시스템에서, 제출할 파이썬 코드 파일을 만드는 것을 주 목적으로 합니다.

**NOTE: this project is currently work-in-progress. 이 프로젝트는 현재 개발중입니다.**

## Usage

Following import statements are supported:

* `from (package_name) import *`
* `from (package_name) import (var_name)`
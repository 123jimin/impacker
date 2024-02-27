# impacker

`impacker`는 파이썬 코드가 참조하는 모든 라이브러리 코드를 단일 파일로 패킹하여, 코드의 의존성을 제거하는 간단한 유틸리티 프로그램입니다.

이 도구는 하나의 소스 코드 파일을 제출해야 하는 온라인 저지 시스템에서, 제출용 파이썬 코드를 생성하기 위해 제작되었습니다.
특히, 프로그래밍 대회 문제 풀이용 라이브러리인 [ckp](https://github.com/123jimin/ckp)와 이 프로젝트는 함께 사용되는 것을 고려하여 개발되었습니다.

## 주요 기능

- 파이썬 코드에서 import하는 다른 코드를 합쳐 하나의 파일로 만들기.
- 트리 셰이킹 (메인 코드에서 사용중인 코드만 포함)
- (계획) 주석 / docstring을 남기거나 제거하기
- (계획) 큰 소스 코드 압축

## 사용 예시

이 코드는 주어진 수가 소수인지 여부를 `ckp`를 이용하여 판별하는 코드입니다.

```py
from ckp.number_theory import is_prime_naive

N = int(input())
print(is_prime_naive(N))
```

이 코드는 `ckp` 없이 독립적으로 돌아갈 수 없습니다.

이 코드의 파일명이 `code.py`이고, 출력 파일의 이름이 `out.py`라고 할 때, impacker는 이렇게 사용할 수 있습니다.

```sh
poetry run python -m impacker code.py out.py
```

`out.py`에는 패킹된 소스 코드가 담겨지며, `ckp` 없이 실행 가능합니다.

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

## 제약 사항

impacker는 `ckp` 이외의 다른 패키지를 패킹하는 데 사용될 수 있지만, 주 목적은 `ckp`를 패킹하는 것입니다. 따라서, `ckp`를 제외한 다른 패키지를 제대로 패킹하지 못할 수 있습니다.

상세하게 말하자면, 현재 impacker는 다음과 같은 제약 사항이 있습니다.

- 모듈을 통째로 임포트 하는 경우에는 합쳐지지 않고, `import`문이 그대로 남습니다.
  - 예시: `import x`, `from x import y` (`x.y`가 모듈인 경우)
  - impacker를 제대로 쓰려면 `from x import y`, `from x import y as z`, `from x import *` 등의 형태를 사용 해 주세요.
  - (`math`, `collections` 등과 같은 빌트인 모듈처럼) 모듈을 합치고 싶지 않다면 상관 없습니다.
- 트리 셰이킹을 하는 경우, 클래스 및 함수 정의만 합쳐집니다.
  - 부작용(side-effect)이 있거나, 전역 변수를 선언하는 모듈은 제대로 작동하지 않을 수 있습니다.
- import문이 조건문이나 함수 등 블록 안에 있는 경우, 제대로 작동하지 않을 수 있습니다.

## 사용 방법

패키지 의존성 관리를 위해서, [Poetry](https://python-poetry.org/) 사용을 *강력하게* 권장합니다.
(Poetry를 사용하지 않는 경우에도 impacker를 사용할 수 있습니다.)

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

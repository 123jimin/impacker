from math import *

class Foo1:
    foo1 = "foo1"

class Foo2(Foo1):
    foo2 = "foo2"

class Foo3(Foo2):
    foo3 = gcd(10, 15)

class Foo(Foo3):
    def __init__(self):
        print(self.foo1, self.foo2, self.foo3)
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import Counter


def disable():
    '''
    Disable a decorator by re-assigning the decorator's name
    to this function. For example, to turn off memoization:

    >>> memo = disable

    '''
    return


def decorator():
    '''
    Decorate a decorator so that it inherits the docstrings
    and stuff from the function it's decorating.
    '''
    return


def countcalls(func):
    '''Decorator that counts calls made to the function decorated.'''
    _counter = Counter()

    def wrapper(*args):
        _counter[func] += 1
        return func(*args)

    wrapper.calls = _counter[func]
    return wrapper


def memo(func):
    '''
    Memoize a function so that it caches all return values for
    faster future lookups.
    '''
    _cache = {}

    def wrapper(*args):
        r = _cache.get(args, None)
        if r is None:
            r = func(*args)
            _cache[args] = r
        return r

    return wrapper


def n_ary(func):
    '''
    Given binary function f(x, y), return an n_ary function such
    that f(x, y, z) = f(x, f(y,z)), etc. Also allow f(x) = x.
    '''

    def wrapper(*args):
        if len(args) == 1:
            return args[0]
        if len(args) == 2:
            return func(*args)
        *s, x, y = args
        return wrapper(*s, func(x, y))

    return wrapper


def trace(func):
    '''Trace calls made to function decorated.

    @trace("____")
    def fib(n):
        ....

    >>> fib(3)
     --> fib(3)
    ____ --> fib(2)
    ________ --> fib(1)
    ________ <-- fib(1) == 1
    ________ --> fib(0)
    ________ <-- fib(0) == 1
    ____ <-- fib(2) == 2
    ____ --> fib(1)
    ____ <-- fib(1) == 1
     <-- fib(3) == 3

    '''

    def wrapper(*args):
        return func(*args)

    return wrapper


@memo
@countcalls
@n_ary
def foo(a, b):
    return a + b


@countcalls
@memo
@n_ary
def bar(a, b):
    return a * b


# @countcalls
# @trace("####")
# @memo
# def fib(n):
#     """Some doc"""
#     return 1 if n <= 1 else fib(n-1) + fib(n-2)


def main():
    print(foo(4, 3))
    print(foo(4, 3, 2))
    print(foo(4, 3))
    print("foo was called", foo.calls, "times")

    print(bar(4, 3))
    print(bar(4, 3, 2))
    print(bar(4, 3, 2, 1))
    print("bar was called", bar.calls, "times")
    print()
    # print(fib.__doc__)
    # fib(3)
    # print(fib.calls, 'calls made')


if __name__ == '__main__':
    main()

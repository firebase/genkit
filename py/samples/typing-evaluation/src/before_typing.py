#!/usr/bin/env python3
"""
BEFORE: Code without proper generic types

This demonstrates what users currently experience - errors at runtime, no autocomplete.
Run: python src/before_typing.py
"""

from typing import Any


def process_user(data: Any) -> Any:
    """Process user data - but what's in data? What do we return?"""
    return {'name': data['name'].upper(), 'age': data['age'] + 1}


class UntypedAction:
    """Simulates current Action class - no generics."""

    def __init__(self, fn: Any):
        self._fn = fn

    def run(self, input: Any) -> dict[str, Any]:
        return {'response': self._fn(input), 'trace_id': '123'}


def demo():
    print('=' * 60)
    print('BEFORE: Runtime Errors with Untyped Code')
    print('=' * 60)

    # Works
    result = process_user({'name': 'alice', 'age': 30})
    print(f'Success: {result}')

    # Fails at RUNTIME - typo in key
    try:
        result = process_user({'naem': 'bob', 'age': 25})
    except KeyError as e:
        print(f'Runtime Error: KeyError - {e}')
        print("  └── IDE didn't catch this typo!")

    # Type information lost through Action
    action = UntypedAction(lambda x: x * x)
    result = action.run(5)
    print(f'\nAction result: {result}')
    print(f"result['response'] type: {type(result['response'])}")
    print('  └── IDE shows: Any - no autocomplete!')

    # This will fail but IDE doesn't know
    try:
        text = result['response'].upper()  # int has no .upper()
    except AttributeError as e:
        print(f'Runtime Error: {e}')
        print("  └── IDE didn't warn that result is int, not str!")


if __name__ == '__main__':
    demo()

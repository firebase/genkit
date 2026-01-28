#!/usr/bin/env python3
"""
AFTER: Code with proper generic types

This demonstrates what users SHOULD experience - IDE autocomplete, errors caught early.
Run: python src/after_typing.py
"""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel


# Define typed models
class UserInput(BaseModel):
    name: str
    age: int


class UserOutput(BaseModel):
    name: str
    age: int


def process_user(data: UserInput) -> UserOutput:
    """Process user data - types are clear!"""
    return UserOutput(name=data.name.upper(), age=data.age + 1)


# Generic Action class - this is what we need
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')


@dataclass
class TypedActionResponse(Generic[OutputT]):
    response: OutputT
    trace_id: str


class TypedAction(Generic[InputT, OutputT]):
    """Action with generics - preserves type information!"""

    def __init__(self, fn: Callable[[InputT], OutputT]):
        self._fn = fn

    def run(self, input: InputT) -> TypedActionResponse[OutputT]:
        return TypedActionResponse(response=self._fn(input), trace_id='123')


def demo():
    print('=' * 60)
    print('AFTER: Type Safety with Generic Classes')
    print('=' * 60)

    # IDE knows: user is UserInput
    user = UserInput(name='alice', age=30)

    # IDE knows: result is UserOutput
    result = process_user(user)

    # Full autocomplete works!
    print(f'Result: {result.name}, {result.age}')

    # Generic action preserves types
    def calculate_square(x: int) -> int:
        return x * x

    # IDE knows: action is TypedAction[int, int]
    action = TypedAction(calculate_square)

    # IDE knows: response is TypedActionResponse[int]
    response = action.run(5)

    # IDE knows: response.response is int
    doubled = response.response * 2
    print(f'\nAction result: {response.response}')
    print(f'Doubled: {doubled}')
    print('  └── IDE knows response.response is int!')

    print('\n' + '=' * 60)
    print('With proper generics:')
    print('  ✅ IDE autocomplete works')
    print('  ✅ Type errors caught before running')
    print('  ✅ Self-documenting code')
    print('=' * 60)


if __name__ == '__main__':
    demo()

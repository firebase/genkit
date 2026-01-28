from __future__ import annotations

from genkit.core.action import Action
from genkit.core.action.types import ActionKind


def identity(x: object) -> object:
    return x


def main() -> None:
    action = Action(
        kind=ActionKind.FLOW,
        name='identity',
        fn=identity,
    )
    result = action.run('anything')
    reveal_type(result)

    value = result.response
    reveal_type(value)

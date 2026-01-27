from __future__ import annotations

from genkit.core.action import Action
from genkit.core.action.types import ActionKind


def int_to_str(x: int) -> str:
    return str(x)


def main() -> None:
    action: Action[int, str] = Action(
        kind=ActionKind.FLOW,
        name="int_to_str",
        fn=int_to_str,
    )
    result = action.run(7)
    reveal_type(result)
    reveal_type(result.response)

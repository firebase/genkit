from typing import Any

from dotpromptz import Dotprompt
from dotpromptz.typing import DataArgument, PromptFunction

dp = Dotprompt()


async def load_prompt_file(path: str) -> PromptFunction:
    with open(path, 'r') as f:
        result = await dp.compile(f.read())

    return result


async def render_text(prompt: PromptFunction, input_: dict[str, Any]) -> str:
    rendered = await prompt(
        data=DataArgument[dict[str, Any]](
            input=input_,
        )
    )
    result = []
    for message in rendered.messages:
        result.append(''.join(e.text for e in message.content))

    return ''.join(result)

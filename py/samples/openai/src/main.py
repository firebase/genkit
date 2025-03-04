# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

from genkit.core.typing import GenerationCommonConfig, Message, TextPart
from genkit.plugins.openai_compat import OpenAI, openai_model
from genkit.veneer.veneer import Genkit
from pydantic import BaseModel, Field

ai = Genkit(plugins=[OpenAI()], model=openai_model('gpt-4'))


class MyInput(BaseModel):
    a: int = Field(description='a field')
    b: int = Field(description='b field')


@ai.flow()
async def say_hi(name: str):
    return await ai.generate(
        model=openai_model('gpt-4'),
        config=GenerationCommonConfig(version='gpt-4-0613', temperature=1),
        messages=[Message(role='user', content=[TextPart(text='hi ' + name)])],
    )


@ai.flow()
def sum_two_numbers2(my_input: MyInput):
    return my_input.a + my_input.b


async def main() -> None:
    print(await say_hi('John Doe'))
    print(sum_two_numbers2(MyInput(a=1, b=3)))


if __name__ == '__main__':
    asyncio.run(main())

# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A hello world sample that just calls some flows."""

from typing import Any

from genkit.core.schema_types import GenerateRequest, Message, Role, TextPart
from genkit.plugins.vertex_ai import GeminiVersion, VertexAI, vertexai_name
from genkit.veneer.veneer import Genkit
from pydantic import BaseModel, Field

ai = Genkit(
    plugins=[VertexAI()],
    model=vertexai_name(str(GeminiVersion.GEMINI_2_0_PRO_EXP.value)),
)


class MyInput(BaseModel):
    a: int = Field(description='a field')
    b: int = Field(description='b field')


def hi_fn(hi_input) -> GenerateRequest:
    return GenerateRequest(
        messages=[
            Message(
                role=Role.user,
                content=[TextPart(text='hi, my name is ' + hi_input)],
            )
        ]
    )


# hi = ai.define_prompt(
#     name="hi",
#     fn=hi_fn,
#     model=gemini("gemini-1.5-flash"))
#
# @ai.flow()
# def hiPrompt():
#     return hi("Pavel")


@ai.flow()
def say_hi(name: str):
    return ai.generate(
        messages=[
            Message(
                role=Role.user,
                content=[TextPart(text='hi ' + name)],
            )
        ]
    )


@ai.flow()
def sum_two_numbers2(my_input: MyInput) -> Any:
    return my_input.a + my_input.b


def main() -> None:
    print(say_hi('John Doe'))
    print(sum_two_numbers2(MyInput(a=1, b=3)))


if __name__ == '__main__':
    main()

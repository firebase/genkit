# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


from genkit.core.types import Message, TextPart, GenerateRequest
from genkit.plugins.vertex_ai import vertexAI, gemini
from genkit.veneer import Genkit
from pydantic import BaseModel, Field

ai = Genkit(plugins=[vertexAI()], model=gemini('gemini-1.5-flash'))


class MyInput(BaseModel):
    a: int = Field(description='a field')
    b: int = Field(description='b field')


def hi_fn(input) -> GenerateRequest:
    return GenerateRequest(
        messages=[
            Message(
                role='user', content=[TextPart(text='hi, my name is ' + input)]
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
def sayHi(input: str):
    return ai.generate(
        messages=[Message(role='user', content=[TextPart(text='hi ' + input)])]
    )


@ai.flow()
def sum_two_numbers2(input: MyInput):
    return input.a + input.b


def main() -> None:
    print(sayHi('John Doe'))
    print(sum_two_numbers2(MyInput(a=1, b=3)))


if __name__ == '__main__':
    main()

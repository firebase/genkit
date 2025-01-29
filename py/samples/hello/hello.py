# Copyright 2025 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

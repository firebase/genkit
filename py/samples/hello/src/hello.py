# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A hello world sample that just calls some flows."""

from typing import Any

from genkit.core.typing import GenerateRequest, Message, Role, TextPart
from genkit.plugins.vertex_ai import VertexAI, vertexai_name
from genkit.veneer.veneer import Genkit
from pydantic import BaseModel, Field

ai = Genkit(
    plugins=[VertexAI()],
    model=vertexai_name(VertexAI.VERTEX_AI_GENERATIVE_MODEL_NAME),
)


class MyInput(BaseModel):
    """Input model for the sum_two_numbers2 function.

    Attributes:
        a: First number to add.
        b: Second number to add.
    """

    a: int = Field(description='a field')
    b: int = Field(description='b field')


def hi_fn(hi_input) -> GenerateRequest:
    """Generate a request to greet a user.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    return GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=f'Say hi to {hi_input}'),
                ],
            ),
        ],
    )


@ai.flow()
def say_hi(name: str):
    """Generate a greeting for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        The generated greeting response.
    """
    return await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'Say hi to {name}')],
            ),
        ],
    )


@ai.flow()
def sum_two_numbers2(my_input: MyInput) -> Any:
    """Add two numbers together.

    Args:
        my_input: A MyInput object containing the two numbers to add.

    Returns:
        The sum of the two numbers.
    """
    return my_input.a + my_input.b


def main() -> None:
    """Main entry point for the hello sample.

    This function demonstrates the usage of the AI flow by generating
    greetings and performing simple arithmetic operations.
    """
    print(say_hi('John Doe'))
    print(sum_two_numbers2(MyInput(a=1, b=3)))


if __name__ == '__main__':
    main()

# Copyright 2025 Google LLC
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
#
# SPDX-License-Identifier: Apache-2.0


from pydantic import BaseModel, Field


class MenuItemSchema(BaseModel):
    """Schema for a menu item."""

    title: str = Field(..., description='The name of the menu item')
    description: str = Field(..., description='Details including ingredients and preparation')
    price: float = Field(..., description='Price in dollars')


class MenuQuestionInputSchema(BaseModel):
    """Input schema for the menu question prompt."""

    question: str = Field(default='What kind of burger buns do you have?', description='A question about the menu')


class AnswerOutputSchema(BaseModel):
    """Output schema for the answer prompt."""

    answer: str = Field(..., description='An answer to a menu-related question')


class DataMenuQuestionInputSchema(BaseModel):
    """Input schema for the data menu question prompt."""

    menuData: list[MenuItemSchema] = Field(...)
    question: str = Field(..., description='A question about the menu')


class TextMenuQuestionInputSchema(BaseModel):
    """Input schema for the text menu question prompt."""

    menu_text: str = Field(
        default="""APPETIZERS
- Mozzarella Sticks $8 - Crispy fried mozzarella sticks served with marinara sauce
- Chicken Wings $10 - Crispy fried chicken wings tossed in your choice of sauce
- Nachos $12 - Crispy tortilla chips topped with melted cheese, chili, sour cream, and salsa

BURGERS & SANDWICHES
- Classic Cheeseburger $12 - A juicy beef patty topped with melted American cheese, lettuce, tomato, and onion on a toasted bun
- Bacon Cheeseburger $14 - A classic cheeseburger with the addition of crispy bacon
- Mushroom Swiss Burger $15 - A beef patty topped with sautéed mushrooms, melted Swiss cheese, and a creamy horseradish sauce
- Chicken Sandwich $13 - A crispy chicken breast on a toasted bun with lettuce, tomato, and your choice of sauce

SALADS
- House Salad $8 - Mixed greens with your choice of dressing
- Caesar Salad $9 - Romaine lettuce with croutons, Parmesan cheese, and Caesar dressing""",
        description='The menu text content',
        alias='menuText',
    )
    question: str = Field(default='What kind of burger buns do you have?', description='A question about the menu')


class MenuToolOutputSchema(BaseModel):
    """Output schema for the menu tool."""

    menu_data: list[MenuItemSchema] = Field(..., description='A list of all the items on the menu')


class ReadMenuImagePromptSchema(BaseModel):
    """Input schema for the read menu image prompt."""

    image_url: str = Field(...)


class ReadMenuPromptOutputSchema(BaseModel):
    """Output schema for the read menu prompt."""

    menu_text: str = Field(...)

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
    title: str = Field(..., description='The name of the menu item')
    description: str = Field(..., description='Details including ingredients and preparation')
    price: float = Field(..., description='Price in dollars')


class MenuQuestionInputSchema(BaseModel):
    question: str = Field(..., description='A question about the menu')


class AnswerOutputSchema(BaseModel):
    answer: str = Field(..., description='An answer to a menu-related question')


class DataMenuQuestionInputSchema(BaseModel):
    menuData: list[MenuItemSchema] = Field(...)
    question: str = Field(..., description='A question about the menu')


class TextMenuQuestionInputSchema(BaseModel):
    menu_text: str = Field(...)
    question: str = Field(..., description='A question about the menu')


class MenuToolOutputSchema(BaseModel):
    menu_data: list[MenuItemSchema] = Field(..., description='A list of all the items on the menu')


class ReadMenuImagePromptSchema(BaseModel):
    image_url: str = Field(...)


class ReadMenuPromptOutputSchema(BaseModel):
    menu_text: str = Field(...)

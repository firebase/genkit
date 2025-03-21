# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field


class MenuItemSchema(BaseModel):
    title: str = Field(..., description='The name of the menu item')
    description: str = Field(
        ..., description='Details including ingredients and preparation'
    )
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
    menu_data: list[MenuItemSchema] = Field(
        ..., description='A list of all the items on the menu'
    )


class ReadMenuImagePromptSchema(BaseModel):
    image_url: str = Field(...)


class ReadMenuPromptOutputSchema(BaseModel):
    menu_text: str = Field(...)

# Copyright 2026 Google LLC
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

from menu_ai import ai
from menu_schemas import AnswerOutputSchema, MenuItemSchema, MenuQuestionInputSchema
from pydantic import BaseModel, Field

from genkit.blocks.document import Document

from .prompts import s04_ragDataMenuPrompt


class IndexMenuItemsOutputSchema(BaseModel):
    rows: int = Field(...)


@ai.flow(name='s04_indexMenuItems')
async def s04_indexMenuItemsFlow(
    menu_items: list[MenuItemSchema],
) -> IndexMenuItemsOutputSchema:
    documents = [
        Document.from_text(f'{item.title} {item.price} \n {item.description}', metadata=item.model_dump())
        for item in menu_items
    ]

    await ai.index(
        indexer='menu-items',
        documents=documents,
    )
    return IndexMenuItemsOutputSchema(rows=len(menu_items))


@ai.flow(name='s04_ragMenuQuestion')
async def s04_ragMenuQuestionFlow(
    my_input: MenuQuestionInputSchema,
) -> AnswerOutputSchema:
    # Retrieve the 3 most relevant menu items for the question
    docs = await ai.retrieve(
        retriever='menu-items',
        query=my_input.question,
        options={'k': 3},
    )

    menu_data = [doc.metadata for doc in docs.documents]

    # Generate the response
    response = await s04_ragDataMenuPrompt({'menuData': menu_data, 'question': my_input.question})
    return AnswerOutputSchema(answer=response.text)

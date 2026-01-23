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


@ai.flow(name='s04_index_menu_items')
async def s04_indexMenuItemsFlow(
    menu_items: list[MenuItemSchema],
) -> IndexMenuItemsOutputSchema:
    # If empty list provided (e.g., from Dev UI default), use the default menu items
    if not menu_items:
        menu_items = [
            MenuItemSchema(
                title='White Meat Crispy Chicken Wings',
                description="All-white meat chicken wings tossed in your choice of wing sauce. Choose from classic buffalo, honey bbq, garlic parmesan, or sweet & sour",
                price=12.0,
            ),
            MenuItemSchema(title='Cheese Fries', description='Fresh fries covered with melted cheddar cheese and bacon', price=8.0),
            MenuItemSchema(
                title='Reuben',
                description='Classic Reuben sandwich with corned beef, sauerkraut, Swiss cheese, and Thousand Island dressing on grilled rye bread.',
                price=12.0,
            ),
            MenuItemSchema(
                title='Grilled Chicken Club Wrap',
                description='Grilled chicken, bacon, lettuce, tomato, pickles, and cheddar cheese wrapped in a spinach tortilla, served with your choice of dressing',
                price=12.0,
            ),
            MenuItemSchema(
                title='Buffalo Chicken Sandwich',
                description='Fried chicken breast coated in your choice of wing sauce, topped with lettuce, tomato, onion, and pickles on a toasted brioche roll.',
                price=12.0,
            ),
            MenuItemSchema(
                title='Half Cuban Sandwich',
                description='Slow roasted pork butt, ham, Swiss, and yellow mustard on a toasted baguette',
                price=12.0,
            ),
            MenuItemSchema(
                title='The Albie Burger',
                description='Classic burger topped with bacon, provolone, banana peppers, and chipotle mayo',
                price=13.0,
            ),
            MenuItemSchema(title='57 Chevy Burger', description='Heaven burger with your choice of cheese', price=14.0),
            MenuItemSchema(
                title='Chicken Caesar Wrap',
                description='Tender grilled chicken, romaine lettuce, croutons, and Parmesan cheese tossed in a creamy Caesar dressing and wrapped in a spinach tortilla',
                price=10.0,
            ),
            MenuItemSchema(title='Kids Hot Dog', description='Kids under 12', price=5.0),
            MenuItemSchema(title='Chicken Fingers', description='Tender chicken strips, grilled or fried', price=8.0),
        ]

    documents = [
        Document.from_text(f'{item.title} {item.price} \n {item.description}', metadata=item.model_dump())
        for item in menu_items
    ]

    await ai.index(
        indexer='menu-items',
        documents=documents,
    )
    return IndexMenuItemsOutputSchema(rows=len(menu_items))


@ai.flow(name='s04_rag_menu_question')
async def s04_ragMenuQuestionFlow(
    my_input: MenuQuestionInputSchema,
) -> AnswerOutputSchema:
    # Retrieve the 3 most relevant menu items for the question
    docs = await ai.retrieve(
        retriever='menu-items',
        query=my_input.question,
        options={'limit': 3},
    )

    menu_data = [doc.metadata for doc in docs.documents]

    # Generate the response
    response = await s04_ragDataMenuPrompt({'menuData': menu_data, 'question': my_input.question})
    return AnswerOutputSchema(answer=response.text)

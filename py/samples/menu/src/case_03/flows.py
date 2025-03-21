# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import json
import os

from case_03.chats import (
    ChatHistoryStore,
    ChatSessionInputSchema,
    ChatSessionOutputSchema,
)
from menu_ai import ai

from genkit.core.typing import Message, Role, TextPart
from genkit.plugins.google_genai.models.gemini import gemini15Flash

menu_json_path = os.path.join('..', '..', 'data', 'menu.json')
with open(menu_json_path, 'r') as f:
    menu_data = json.load(f)

formatted_menu_data = '\n'.join([
    f'- ${r.title} ${r.price}\n${r.description}' for r in menu_data
])

preamble = [
    Message(
        role=Role.USER,
        content=[
            TextPart(text=f"Hi. What's on the menu today?"),
        ],
    ),
    Message(
        role=Role.USER,
        content=[
            TextPart(
                text=f"""I am Walt, a helpful AI assistant here at the restaurant.\n' +
                          'I can answer questions about the food on the menu or any other questions\n' +
                          "you have about food in general. I probably can't help you with anything else.\n" +
                          "Here is today's menu: \n {formatted_menu_data}\nDo you have any questions about the menu?"""
            ),
        ],
    ),
]

chat_history_store = ChatHistoryStore(
    preamble=preamble,
)


@ai.flow(name='s03_multiTurnChat')
async def s03_multiTurnChatFlow(
    my_input: ChatSessionInputSchema,
) -> ChatSessionOutputSchema:
    history = chat_history_store.read(my_input.session_id)

    llm_response = await ai.generate(
        model=gemini15Flash,
        messages=history,
        prompt=[TextPart(text=my_input.question)],
    )

    history = llm_response.messages

    chat_history_store.write(my_input.session_id, history)

    return ChatSessionOutputSchema(
        session_id=my_input.session_id,
        history=history,
    )

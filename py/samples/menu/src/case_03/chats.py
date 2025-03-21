# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel

from genkit.core.typing import Message


class ChatSessionInputSchema(BaseModel):
    session_id: str
    question: str


class ChatSessionOutputSchema(BaseModel):
    session_id: str
    history: list[Message]


ChatHistory = list[Message]


class ChatHistoryStore:
    def __init__(self, preamble: ChatHistory | None = None):
        self.preamble = preamble if preamble is not None else []
        self.sessions: dict[str, ChatHistory] = {}

    def write(self, session_id: str, history: ChatHistory):
        self.sessions[session_id] = history

    def read(self, session_id: str) -> ChatHistory:
        return self.sessions.get(session_id, self.preamble)

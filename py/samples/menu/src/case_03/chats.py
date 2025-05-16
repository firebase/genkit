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

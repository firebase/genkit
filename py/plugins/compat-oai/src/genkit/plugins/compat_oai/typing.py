# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    role: str
    content: str


class OpenAIConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    model: str | None = None
    top_p: float | None = None
    temperature: float | None = None
    stop: str | list[str] | None = None
    max_tokens: int | None = None
    stream: bool | None = None

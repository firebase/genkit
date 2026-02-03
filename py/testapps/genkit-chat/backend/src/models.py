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

"""Pydantic models for API request/response schemas.

These models define the data structures used by the REST API endpoints.
They provide validation, serialization, and documentation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description='Message content text')


class ChatConfig(BaseModel):
    """Configuration options for chat generation."""

    temperature: float = Field(0.7, ge=0.0, le=2.0, description='Sampling temperature')
    max_tokens: int = Field(1024, ge=1, le=100000, description='Maximum output tokens')
    top_p: float = Field(1.0, ge=0.0, le=1.0, description='Top-p sampling')
    top_k: int = Field(40, ge=1, description='Top-k sampling')


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    model: str = Field(..., description="Model ID (e.g., 'googleai/gemini-3-flash-preview')")
    messages: list[Message] = Field(..., description='Conversation messages')
    config: ChatConfig | None = Field(None, description='Generation config')
    conversation_id: str | None = Field(None, description='Optional conversation ID')


class UsageStats(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = Field(0, description='Input tokens')
    completion_tokens: int = Field(0, description='Output tokens')
    total_tokens: int = Field(0, description='Total tokens')


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    message: Message = Field(..., description="Assistant's response message")
    model: str = Field(..., description='Model used for generation')
    latency_ms: int = Field(..., description='Response time in milliseconds')
    usage: UsageStats | None = Field(None, description='Token usage stats')


class ModelCapabilities(BaseModel):
    """Model capabilities enum values."""

    TEXT: str = 'text'
    VISION: str = 'vision'
    AUDIO: str = 'audio'
    VIDEO: str = 'video'
    STREAMING: str = 'streaming'


class ModelInfo(BaseModel):
    """Information about a single model."""

    id: str = Field(..., description="Model ID (e.g., 'googleai/gemini-3-flash-preview')")
    name: str = Field(..., description='Display name')
    capabilities: list[str] = Field(default_factory=list, description='Supported capabilities')
    context_window: int = Field(4096, description='Maximum context window size')


class ProviderInfo(BaseModel):
    """Information about a model provider."""

    id: str = Field(..., description="Provider ID (e.g., 'google-genai')")
    name: str = Field(..., description='Display name')
    available: bool = Field(..., description='Whether provider is configured')
    models: list[ModelInfo] = Field(default_factory=list, description='Available models')


class ModelsResponse(BaseModel):
    """Response from models listing endpoint."""

    providers: list[ProviderInfo] = Field(default_factory=list, description='Available providers')


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""

    id: str = Field(..., description='Conversation ID')
    title: str = Field(..., description='Conversation title')
    created_at: str = Field(..., description='ISO timestamp of creation')
    message_count: int = Field(0, description='Number of messages')
    pinned: bool = Field(False, description='Whether conversation is pinned')


class Conversation(BaseModel):
    """Full conversation with messages."""

    id: str = Field(..., description='Conversation ID')
    title: str = Field(..., description='Conversation title')
    created_at: str = Field(..., description='ISO timestamp of creation')
    updated_at: str = Field(..., description='ISO timestamp of last update')
    messages: list[Message] = Field(default_factory=list, description='All messages')
    model: str | None = Field(None, description='Preferred model for this conversation')
    pinned: bool = Field(False, description='Whether conversation is pinned')


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description='Error message')
    code: str | None = Field(None, description='Error code')
    details: dict[str, Any] | None = Field(None, description='Additional details')

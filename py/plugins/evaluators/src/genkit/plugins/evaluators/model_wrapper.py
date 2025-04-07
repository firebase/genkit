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

import asyncio
from typing import Any

import structlog
from langchain_core.callbacks import Callbacks
from langchain_core.outputs import LLMResult
from langchain_core.outputs.generation import Generation
from langchain_core.prompt_values import PromptValue
from pydantic import BaseModel
from ragas.llms.base import BaseRagasLLM

from genkit.ai import GenkitRegistry

logger = structlog.get_logger(__name__)


class GenkitModel(BaseRagasLLM):
    """Wrapper to enable Genkit Models in RAGAS."""

    def __init__(self, ai: GenkitRegistry, model: str, config: BaseModel | dict[str, Any] | None = None):
        """Initialize a Genkit model as a Ragas Model."""
        super().__init__()
        self.ai = ai
        self.model = model
        self.config = config.dict() if isinstance(config, BaseModel) else config

    def generate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float = 1e-8,
        stop: list[str] | None = None,
        callbacks: Callbacks = None,
    ) -> LLMResult:
        """Run ai.generate on the prompt."""
        return asyncio.run(self.agenerate_text(prompt, n, temperature, stop, callbacks))

    async def agenerate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: float | None = None,
        stop: list[str] | None = None,
        callbacks: Callbacks = None,
    ) -> LLMResult:
        """Run ai.agenerate on the prompt."""
        prompt = prompt.to_string()

        config = self.config if self.config is not None else {}

        if temperature is not None:
            config['temperature'] = temperature

        response = await self.ai.agenerate(model=self.model, config=self.config, prompt=prompt)
        text = response.text
        return LLMResult(generations=[[Generation(text=text)]])

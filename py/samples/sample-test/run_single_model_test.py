#!/usr/bin/env python3
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

"""Helper script to run a single model test in isolation.

This script is called by test_model_performance.py to execute each model+config
test in a separate subprocess, avoiding state pollution and enabling timeout handling.

Usage:
    python run_single_model_test.py <model_name> --config <json_config> --user-prompt <text> --system-prompt <text>

Output:
    JSON object with 'success', 'response', 'error', 'timing' fields
"""

import argparse
import json
import sys
import time
from typing import Any


async def run_model_test(
    model_name: str,
    config: dict[str, Any],
    user_prompt: str,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Run a single model test and return result.

    Args:
        model_name: Name of the model to test
        config: Configuration dictionary for the model
        user_prompt: User prompt to send
        system_prompt: Optional system prompt

    Returns:
        Dict with 'success', 'response', 'error', 'timing' fields
    """
    result: dict[str, Any] = {
        "success": False,
        "response": None,
        "error": None,
        "timing": 0.0,
    }

    try:
        # Import Genkit
        from genkit import Genkit
        from genkit.plugins.google_genai import GoogleAI, VertexAI
        from genkit.core.typing import Message, TextPart

        plugins = []
        try:
            plugins.append(GoogleAI())
        except Exception:
            pass
        try:
            plugins.append(VertexAI())
        except Exception:
            pass

        # Initialize Genkit
        ai = Genkit(plugins=plugins)

        # Build the prompt
        messages = []
        if system_prompt:
            messages.append(Message(
                role='system',
                content=[TextPart(text=system_prompt)]
            ))
        messages.append(Message(
            role='user',
            content=[TextPart(text=user_prompt)]
        ))

        # Start timing
        start_time = time.time()

        # Run generation
        response = await ai.generate(
            model=model_name,
            messages=messages,
            config=config,
        )

        # Calculate timing
        elapsed = time.time() - start_time

        # Extract response text
        response_text = response.text if hasattr(response, 'text') else str(response)

        result["success"] = True
        result["response"] = response_text
        result["timing"] = round(elapsed, 3)

    except Exception as e:
        import traceback
        result["error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

    return result


def main() -> None:
    """Run a single model test and output JSON result."""
    parser = argparse.ArgumentParser(description='Run a single model test.')
    parser.add_argument('model_name', type=str, help='Name of the model to test')
    parser.add_argument('--config', type=str, default='{}', help='JSON string of model config')
    parser.add_argument('--user-prompt', type=str, required=True, help='User prompt text')
    parser.add_argument('--system-prompt', type=str, default=None, help='System prompt text')
    args = parser.parse_args()

    # Suppress verbose logging
    import logging
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger('genkit').setLevel(logging.ERROR)
    logging.getLogger('google').setLevel(logging.ERROR)

    # Override input() to prevent blocking
    import builtins
    builtins.input = lambda prompt="": "dummy_value"

    result: dict[str, Any] = {"success": False, "response": None, "error": "Unknown initialization error", "timing": 0.0}

    try:
        # Parse config
        config = json.loads(args.config)

        # Run test in async context
        import asyncio
        result = asyncio.run(run_model_test(
            args.model_name,
            config,
            args.user_prompt,
            args.system_prompt,
        ))

    except Exception as e:
        result = {"success": False, "response": None, "error": f"Initialization failed: {e}", "timing": 0.0}

    # Output JSON result with markers
    print("---JSON_RESULT_START---")
    print(json.dumps(result))
    print("---JSON_RESULT_END---")


if __name__ == "__main__":
    main()

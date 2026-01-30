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

"""Google Checks AI Safety Demo.

This sample demonstrates how to use the Google Checks AI safety plugin for
content moderation in Genkit applications. Checks provides real-time content
classification to detect policy violations before they reach your users.

What is Google Checks?
======================

Google Checks (https://checks.google.com/ai-safety) is an AI safety platform
that provides:

- **Guardrails API**: Real-time content classification for policy violations
- **Automated Adversarial Testing**: Offline evaluation of your model's safety

Two Usage Patterns
==================

1. **Middleware** - Apply checks in real-time within ai.generate() calls:

    response = await ai.generate(
        model='googleai/gemini-2.0-flash',
        prompt=topic,
        use=[
            checks_middleware(
                metrics=[ChecksMetricType.DANGEROUS_CONTENT],
                auth_options={'project_id': 'your-project'},
            )
        ],
    )

2. **Evaluator Plugin** - Configure as a plugin for offline evaluation:

    ai = Genkit(
        plugins=[
            Checks(
                project_id='your-project',
                evaluation={
                    'metrics': [
                        ChecksMetricType.DANGEROUS_CONTENT,
                        ChecksMetricConfig(
                            type=ChecksMetricType.HARASSMENT,
                            threshold=0.6,
                        ),
                    ]
                },
            )
        ]
    )

Testing the Demo
================

1. Run the sample: ./run.sh
2. Open Dev UI at http://localhost:4000
3. Run the flows:
   - poem_with_guardrails: Generates a poem with Checks middleware
   - poem_without_guardrails: Generates a poem without safety checks

Test with these inputs:
- Benign: "Write a poem about nature"
- Edge case: Test potentially unsafe inputs to see guardrails in action

Note:
====

The Guardrails API is in private preview. Request quota at:
https://docs.google.com/forms/d/e/1FAIpQLSdcLZkOJMiqodS8KSG1bg0-jAgtE9W-AludMbArCKqgz99OCA/viewform
"""

import os

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI

install_rich_traceback(show_locals=True, width=120, extra_lines=3)


class PoemInput(BaseModel):
    """Input for poem generation flows."""

    topic: str = Field(
        default='Write a short poem about the beauty of nature',
        description='Topic or prompt for the poem',
    )


# Get project ID from environment
PROJECT_ID = os.environ.get('GCLOUD_PROJECT', os.environ.get('GOOGLE_CLOUD_PROJECT', 'your-project-id'))


# Initialize Genkit with GoogleAI and optionally Checks plugins
ai = Genkit(
    plugins=[
        GoogleAI(),
        # Configure Checks for offline evaluation
        # Uncomment when you have Checks API quota
        # Checks(
        #     project_id=PROJECT_ID,
        #     evaluation={
        #         'metrics': [
        #             ChecksMetricType.DANGEROUS_CONTENT,
        #             ChecksMetricType.HARASSMENT,
        #             ChecksMetricType.HATE_SPEECH,
        #             # Custom threshold for violence (more restrictive)
        #             ChecksMetricConfig(
        #                 type=ChecksMetricType.VIOLENCE_AND_GORE,
        #                 threshold=0.3,
        #             ),
        #         ]
        #     },
        # ),
    ],
)


@ai.flow()
async def poem_with_guardrails(input: PoemInput) -> str:
    """Generate a poem with Checks guardrails applied.

    This flow demonstrates using Checks middleware to filter both
    input and output content for policy violations. If content
    violates configured policies, the response will be blocked.

    Args:
        input: The poem topic and configuration.

    Returns:
        Generated poem text, or an error message if blocked.
    """
    response = await ai.generate(
        model='googleai/gemini-2.0-flash',
        prompt=input.topic,
        # Apply Checks middleware for real-time content filtering
        # Uncomment when you have Checks API quota
        # use=[
        #     checks_middleware(
        #         auth_options={'project_id': PROJECT_ID},
        #         metrics=[
        #             # Use default threshold
        #             ChecksMetricType.DANGEROUS_CONTENT,
        #             ChecksMetricType.HARASSMENT,
        #             # Custom threshold (lower = more restrictive)
        #             ChecksMetricConfig(
        #                 type=ChecksMetricType.VIOLENCE_AND_GORE,
        #                 threshold=0.3,
        #             ),
        #         ],
        #     )
        # ],
    )

    # Check if response was blocked by guardrails
    if response.finish_reason == 'blocked':
        return f'⚠️ Content blocked by safety guardrails: {response.finish_message}'

    return response.text or ''


@ai.flow()
async def poem_without_guardrails(input: PoemInput) -> str:
    """Generate a poem without safety guardrails.

    This flow generates content without applying Checks middleware,
    useful for comparison or when guardrails are not needed.

    Args:
        input: The poem topic and configuration.

    Returns:
        Generated poem text.
    """
    response = await ai.generate(
        model='googleai/gemini-2.0-flash',
        prompt=input.topic,
    )
    return response.text or ''


@ai.flow()
async def compare_safety_policies(input: PoemInput) -> dict[str, str]:
    """Compare output with and without safety guardrails.

    This flow runs the same prompt through both guarded and
    unguarded generation to demonstrate the effect of Checks.

    Args:
        input: The poem topic and configuration.

    Returns:
        Dictionary with 'guarded' and 'unguarded' results.
    """
    guarded = await poem_with_guardrails(input)
    unguarded = await poem_without_guardrails(input)

    return {
        'guarded': guarded,
        'unguarded': unguarded,
        'note': 'Compare the results to see guardrail effects',
    }


if __name__ == '__main__':
    # Simple test run
    import asyncio

    async def main() -> None:
        """Run the sample to test poem generation."""
        result = await poem_without_guardrails(PoemInput())
        print('Generated poem:')
        print(result)

    asyncio.run(main())

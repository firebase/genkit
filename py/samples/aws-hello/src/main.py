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

"""AWS Telemetry Demo for Genkit.

This sample demonstrates how to export telemetry (traces) from Genkit to AWS X-Ray
using the AWS plugin. The traces provide visibility into flow execution, model
calls, and any errors that occur.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Telemetry           │ Data about how your app runs. Like a fitness      │
    │                     │ tracker for your code - tracks what happens.      │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Trace               │ The full story of one request. Shows every step   │
    │                     │ from start to finish (flow → model → response).   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ X-Ray               │ AWS service that collects and shows traces.       │
    │                     │ Like a detective board connecting all the clues.  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Span                │ One step in a trace. "Called Gemini model" or     │
    │                     │ "Ran hello_world flow" - each is a span.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ PII Redaction       │ Hiding sensitive data in traces. We don't send    │
    │                     │ your actual prompts/responses by default.         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Region              │ Which AWS data center to use. Set AWS_REGION      │
    │                     │ to your nearest region (us-west-2, etc.).         │
    └─────────────────────┴────────────────────────────────────────────────────┘

Architecture Overview::

    ┌────────────────────────────────────────────────────────────────────────┐
    │                    AWS Telemetry Demo                                  │
    ├────────────────────────────────────────────────────────────────────────┤
    │  1. Configure AWS telemetry with add_aws_telemetry()                   │
    │  2. Configure Google GenAI model (or any model provider)               │
    │  3. Run flows - traces are automatically exported to X-Ray             │
    └────────────────────────────────────────────────────────────────────────┘

    Data Flow:
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │ Genkit Flow  │───►│ OpenTelemetry│───►│ AWS X-Ray    │
    │ (model call) │    │ SDK          │    │ Console      │
    └──────────────┘    └──────────────┘    └──────────────┘

Prerequisites:
    1. AWS credentials configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, or IAM role)
    2. AWS_REGION environment variable set
    3. GOOGLE_GENAI_API_KEY environment variable set
    4. IAM policy: AWSXrayWriteOnlyPolicy attached to your role/user

Running the Demo:
    1. Set environment variables:
       export AWS_REGION=us-west-2
       export GOOGLE_GENAI_API_KEY=your-api-key

    2. Run the sample:
       ./run.sh

    3. Open the Dev UI (typically at http://localhost:4000)

    4. Run the 'hello_world' flow

    5. View traces in AWS X-Ray Console:
       https://console.aws.amazon.com/xray/home

Expected Output:
    - Traces appear in X-Ray within 1-2 minutes
    - Each trace shows: flow name, model calls, latency, errors
    - Use X-Ray to debug performance issues and errors

See Also:
    - AWS X-Ray Console: https://console.aws.amazon.com/xray/home
    - AWS X-Ray Documentation: https://docs.aws.amazon.com/xray/
    - Genkit Observability: https://genkit.dev/docs/observability
"""

from rich.traceback import install as install_rich_traceback

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

import asyncio

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.aws import add_aws_telemetry
from genkit.plugins.google_genai import GoogleAI

logger = structlog.get_logger(__name__)


class HelloInput(BaseModel):
    """Input for the hello world flow."""

    prompt: str = Field(
        default='Tell me a short fun fact about AWS X-Ray tracing.',
        description='A prompt for the model',
    )


# Enable AWS X-Ray telemetry
# Traces will be exported to the AWS region specified in AWS_REGION
add_aws_telemetry()

# Configure the model provider
# You can use any model provider - we use Google GenAI here for simplicity
ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.0-flash',
)


@ai.flow()
async def hello_world(input: HelloInput) -> str:
    """A simple flow that generates text and exports traces to X-Ray.

    This flow demonstrates AWS X-Ray telemetry integration:
    - Flow execution is traced
    - Model calls are traced
    - Latency and metadata are captured
    - Errors (if any) are recorded

    Args:
        input: The input containing the prompt.

    Returns:
        The generated text response.

    Example:
        Run this flow from the Dev UI with the default prompt to see
        traces appear in the AWS X-Ray console.
    """
    logger.info('Generating response with X-Ray tracing enabled')

    response = await ai.generate(prompt=input.prompt)

    logger.info('Response generated successfully', length=len(response.text or ''))

    return response.text or 'No response generated'


@ai.flow()
async def multi_step_demo(input: HelloInput) -> str:
    """A multi-step flow to demonstrate nested trace spans.

    This flow shows how nested operations appear in X-Ray traces:
    - Parent span: multi_step_demo flow
    - Child spans: multiple ai.generate calls

    Args:
        input: The input containing the initial prompt.

    Returns:
        The final summarized response.
    """
    logger.info('Starting multi-step flow')

    # Step 1: Generate initial response
    step1 = await ai.generate(prompt=f'In 1-2 sentences: {input.prompt}')
    logger.info('Step 1 complete')

    # Step 2: Expand on the response
    step2 = await ai.generate(prompt=f'Add one more interesting detail to: {step1.text}')
    logger.info('Step 2 complete')

    # Step 3: Summarize
    step3 = await ai.generate(prompt=f'Combine these into a single coherent paragraph: {step1.text} {step2.text}')
    logger.info('Step 3 complete - multi-step flow finished')

    return step3.text or 'No response generated'


async def main() -> None:
    """Run the Genkit server with AWS telemetry enabled.

    The server will start and traces will be exported to AWS X-Ray.
    View traces at: https://console.aws.amazon.com/xray/home
    """
    logger.info('Starting AWS Telemetry demo', flows=['hello_world', 'multi_step_demo'])
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())

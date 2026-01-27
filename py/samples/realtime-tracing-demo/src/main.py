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

"""Realtime Tracing Demo - Watch spans appear as they start.

This sample demonstrates Genkit's realtime tracing feature, which exports
spans to the DevUI as they START (not just when they complete).

Key Features
============
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Feature                   │ Description                                 │
    ├───────────────────────────┼─────────────────────────────────────────────┤
    │ RealtimeSpanProcessor     │ Exports spans on start AND end              │
    │ Multi-step flows          │ Watch each step appear in real-time         │
    │ Nested actions            │ See parent/child relationships live         │
    │ Long-running operations   │ Monitor progress of slow tasks              │
    └───────────────────────────┴─────────────────────────────────────────────┘

Testing This Demo
=================
1. **Prerequisites**:
   ```bash
   export GEMINI_API_KEY=your_api_key
   ```
   Or the demo will prompt for the key interactively.

2. **Run the demo**:
   ```bash
   cd py/samples/realtime-tracing-demo
   ./run.sh  # This sets GENKIT_ENABLE_REALTIME_TELEMETRY=true
   ```

3. **Open DevUI** at http://localhost:4000

4. **Test realtime tracing**:
   - [ ] Open the Traces tab in DevUI
   - [ ] Trigger a multi-step flow
   - [ ] Watch spans appear IMMEDIATELY as they start
   - [ ] Compare to non-realtime (spans appear at end)

5. **Test flows**:
   - [ ] `multi_step_flow` - See each step appear in order
   - [ ] `nested_flow` - See parent/child span hierarchy
   - [ ] `long_running_flow` - Watch progress of slow tasks

6. **Expected behavior**:
   - Spans appear in DevUI as soon as they START
   - You see "in progress" spans while they're running
   - Nested spans show proper parent/child relationships
   - Long-running spans show duration updating in real-time

Environment Variables
=====================
    GENKIT_ENABLE_REALTIME_TELEMETRY=true  # Enable realtime tracing
    GENKIT_TELEMETRY_SERVER=http://...     # Telemetry server URL (auto-set)
"""

import asyncio
import os
import sys

import structlog

from genkit.ai import Genkit
from genkit.core.trace import is_realtime_telemetry_enabled
from genkit.plugins.google_genai import GoogleAI

logger = structlog.get_logger(__name__)


def _ensure_api_key() -> None:
    """Prompt for GEMINI_API_KEY if not set."""
    if not os.environ.get('GEMINI_API_KEY'):
        print('GEMINI_API_KEY is not set.')
        try:
            api_key = input('Enter your Gemini API key: ').strip()
            if api_key:
                os.environ['GEMINI_API_KEY'] = api_key
            else:
                print('Error: API key cannot be empty.')
                sys.exit(1)
        except (EOFError, KeyboardInterrupt):
            print('\nError: GEMINI_API_KEY is required.')
            sys.exit(1)


_ensure_api_key()

# Initialize Genkit
ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.0-flash',
)


# =============================================================================
# FLOWS FOR DEMONSTRATING REALTIME TRACING
# =============================================================================


@ai.flow(name='slow_multi_step')
async def slow_multi_step_flow(topic: str = 'Python programming') -> dict:
    """A multi-step flow with delays to demonstrate realtime tracing.

    Watch the DevUI as each step appears immediately when it starts!

    Args:
        topic: The topic to process.

    Returns:
        A dict with results from each step.
    """
    results = {}

    # Step 1: Research (appears immediately in DevUI)
    logger.info('Starting Step 1: Research', topic=topic)
    research = await ai.run(
        'research',
        lambda: slow_operation(f'Researching {topic}', delay=2.0),
    )
    results['research'] = research

    # Step 2: Analysis (appears as soon as Step 1 completes)
    logger.info('Starting Step 2: Analysis')
    analysis = await ai.run(
        'analysis',
        lambda: slow_operation('Analyzing research findings', delay=1.5),
    )
    results['analysis'] = analysis

    # Step 3: Generate Summary (uses actual LLM)
    logger.info('Starting Step 3: Generate Summary with LLM')
    response = await ai.generate(
        prompt=f'Write a one-sentence summary about {topic}.',
        config={'temperature': 0.7},
    )
    results['summary'] = response.text

    return results


@ai.flow(name='nested_operations')
async def nested_operations_flow(depth: int = 3) -> str:
    """A flow with nested operations to show parent/child relationships.

    In the DevUI, you'll see the hierarchy of spans as they execute.

    Args:
        depth: How deep to nest operations.

    Returns:
        A completion message.
    """

    async def nested_step(level: int) -> str:
        """Recursive nested operation."""
        if level <= 0:
            return 'Done!'

        return await ai.run(
            f'level_{level}',
            lambda: nested_step(level - 1),
        )

    result = await nested_step(depth)
    return f'Completed {depth} levels: {result}'


@ai.flow(name='parallel_tasks')
async def parallel_tasks_flow(num_tasks: int = 3) -> list[str]:
    """Run multiple tasks in parallel to see concurrent spans.

    In the DevUI with realtime tracing, you'll see all tasks
    start simultaneously and complete at different times.

    Args:
        num_tasks: Number of parallel tasks to run.

    Returns:
        List of results from each task.
    """
    tasks = []

    for i in range(num_tasks):
        delay = 1.0 + (i * 0.5)  # Staggered completion times

        async def task_fn(task_id: int = i, task_delay: float = delay) -> str:
            await asyncio.sleep(task_delay)
            return f'Task {task_id} completed after {task_delay}s'

        tasks.append(ai.run(f'parallel_task_{i}', task_fn))

    results = await asyncio.gather(*tasks)
    return list(results)


@ai.flow(name='llm_chain')
async def llm_chain_flow(initial_prompt: str = 'Tell me a fun fact') -> dict:
    """Chain multiple LLM calls to see sequential model invocations.

    Each model call will appear as a separate span in the DevUI.

    Args:
        initial_prompt: The starting prompt.

    Returns:
        Dict with responses from each step.
    """
    results = {}

    # Step 1: Initial generation
    response1 = await ai.generate(
        prompt=initial_prompt,
        config={'maxOutputTokens': 100},
    )
    results['fact'] = response1.text

    # Step 2: Follow-up question
    response2 = await ai.generate(
        prompt=f'Based on this fact: "{response1.text[:100]}...", ask a follow-up question.',
        config={'maxOutputTokens': 50},
    )
    results['question'] = response2.text

    # Step 3: Answer the follow-up
    response3 = await ai.generate(
        prompt=f'Answer this question: {response2.text}',
        config={'maxOutputTokens': 100},
    )
    results['answer'] = response3.text

    return results


@ai.flow(name='check_realtime_status')
async def check_realtime_status() -> dict:
    """Check if realtime tracing is enabled.

    Returns:
        Status information about realtime tracing.
    """
    enabled = is_realtime_telemetry_enabled()
    telemetry_server = os.environ.get('GENKIT_TELEMETRY_SERVER', 'Not set')

    return {
        'realtime_enabled': enabled,
        'telemetry_server': telemetry_server,
        'env_var': os.environ.get('GENKIT_ENABLE_REALTIME_TELEMETRY', 'Not set'),
        'message': (
            'Realtime tracing is ENABLED! Spans appear immediately in DevUI.'
            if enabled
            else 'Realtime tracing is DISABLED. Set GENKIT_ENABLE_REALTIME_TELEMETRY=true to enable.'
        ),
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


async def slow_operation(description: str, delay: float = 1.0) -> str:
    """Simulate a slow operation.

    Args:
        description: What the operation is doing.
        delay: How long to wait in seconds.

    Returns:
        A completion message.
    """
    logger.info('Starting slow operation', description=description, delay=delay)
    await asyncio.sleep(delay)
    logger.info('Completed slow operation', description=description)
    return f'Completed: {description}'


# =============================================================================
# MAIN
# =============================================================================


async def main() -> None:
    """Main entry point - keeps the server running for DevUI."""
    import asyncio

    enabled = is_realtime_telemetry_enabled()
    if enabled:
        await logger.ainfo('Realtime tracing ENABLED. Spans appear in DevUI immediately.')
    else:
        await logger.ainfo('Realtime tracing DISABLED. Set GENKIT_ENABLE_REALTIME_TELEMETRY=true.')

    await logger.ainfo('Realtime Tracing Demo running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())

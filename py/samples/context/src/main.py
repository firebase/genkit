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

"""Context propagation — pass context to ai.generate(), read via ctx.context or Genkit.current_context()."""

import os

import structlog
from pydantic import BaseModel, Field

from genkit import Genkit
from genkit._core._action import ActionRunContext
from genkit.plugins.google_genai import GoogleAI

if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.5-flash',
)


def _user_from_context(context: dict[str, object]) -> tuple[int, dict[str, str]]:
    """Extract user_id and record from a context dict.

    Args:
        context: The Genkit action context dict.

    Returns:
        A (user_id, record) tuple with defaults for unknown users.
    """
    default_record: dict[str, str] = {'name': 'Unknown', 'role': 'unknown', 'plan': 'none'}
    raw_user = context.get('user')
    if not isinstance(raw_user, dict):
        return 0, default_record
    user_id = int(raw_user.get('id', 0))  # type: ignore[arg-type]
    return user_id, MOCK_USER_DB.get(user_id, default_record)


MOCK_USER_DB: dict[int, dict[str, str]] = {
    42: {'name': 'Arthur Dent', 'role': 'intergalactic traveler', 'plan': 'premium'},
    123: {'name': 'Jane Doe', 'role': 'engineer', 'plan': 'enterprise'},
    999: {'name': 'Guest User', 'role': 'visitor', 'plan': 'free'},
}


class ContextInput(BaseModel):
    """Input for context demo flows."""

    user_id: int = Field(default=42, description='User ID to look up (try 42, 123, or 999)')


@ai.tool()
async def get_user_info() -> str:
    """Look up the current user from context.

    This tool takes no explicit input -- it reads the user ID from the
    execution context that was passed to ai.generate(context=...).

    Returns:
        A description of the user.
    """
    context = Genkit.current_context() or {}
    _, record = _user_from_context(context)
    return f'{record["name"]} ({record["role"]}, {record["plan"]} plan)'


@ai.tool()
async def get_user_via_static() -> str:
    """Look up the current user using Genkit.current_context().

    Demonstrates the static method approach -- useful when context is needed
    deep in a call stack where ctx isn't easily threaded through.

    Returns:
        A description of the user from the static context accessor.
    """
    context = Genkit.current_context()
    if context is None:
        return 'No context available (not running inside an action).'
    user = context.get('user', {})
    user_id = user.get('id')
    record = MOCK_USER_DB.get(user_id, {'name': 'Unknown', 'role': 'unknown', 'plan': 'none'})
    return f'[via current_context()] {record["name"]} ({record["role"]}, {record["plan"]} plan)'


@ai.tool()
async def get_user_permissions() -> str:
    """Return permissions based on the user's plan from context.

    Used in the propagation chain demo to verify context survives
    through nested generate calls.

    Returns:
        Permission level description.
    """
    context = Genkit.current_context() or {}
    _, record = _user_from_context(context)
    permissions = {
        'free': 'read-only access',
        'premium': 'read-write access with priority support',
        'enterprise': 'full admin access with SLA guarantees',
        'none': 'no access',
    }
    return f'{record["name"]} has {permissions.get(record["plan"], "unknown")} ({record["plan"]} plan)'


@ai.flow()
async def context_in_generate(input: ContextInput) -> str:
    """Pass context to ai.generate() and let a tool read it.

    This is the simplest context pattern: the caller provides context
    as a dictionary, and tools receive it via ``ctx.context``.

    Args:
        input: Input with user ID.

    Returns:
        Model response incorporating user-specific tool output.
    """
    response = await ai.generate(
        prompt='Look up the current user and describe who they are.',
        tools=['get_user_info'],
        context={'user': {'id': input.user_id}},
    )
    return response.text


@ai.flow()
async def context_in_flow(input: ContextInput, ctx: ActionRunContext) -> str:
    """Access context directly inside a flow.

    When a flow is invoked with context (e.g., from the DevUI or another
    flow), the ``ActionRunContext`` parameter provides access to it.

    Args:
        input: Input with user ID.
        ctx: Execution context provided by Genkit.

    Returns:
        Description of what context the flow sees.
    """
    flow_context = ctx.context
    await logger.ainfo('Flow context received', context=flow_context)

    response = await ai.generate(
        prompt=(f'The flow received this context: {flow_context}. Also look up the user info using the tool.'),
        tools=['get_user_info'],
        context={'user': {'id': input.user_id}},
    )
    return response.text


@ai.flow()
async def context_current_context(input: ContextInput) -> str:
    """Demonstrate Genkit.current_context() static method.

    The tool in this flow uses ``Genkit.current_context()`` instead of
    ``ctx.context`` to read the execution context. This is useful when
    context is needed deep in a call stack where the ToolRunContext
    object isn't directly available.

    Args:
        input: Input with user ID.

    Returns:
        Model response using the static context accessor.
    """
    response = await ai.generate(
        prompt='Look up the current user using the static context method and describe them.',
        tools=['get_user_via_static'],
        context={'user': {'id': input.user_id}},
    )
    return response.text


@ai.flow()
async def context_propagation_chain(input: ContextInput) -> str:
    """Verify context propagates through nested generate/tool chains.

    This flow calls ai.generate() with context, which triggers a tool.
    That tool's response is then fed into a second ai.generate() call
    (without explicitly passing context again) to verify that context
    is automatically inherited through the ContextVar mechanism.

    Args:
        input: Input with user ID.

    Returns:
        Combined response showing context survived multiple levels.
    """
    first_response = await ai.generate(
        prompt='Look up the current user info.',
        tools=['get_user_info'],
        context={'user': {'id': input.user_id}},
    )

    second_response = await ai.generate(
        prompt=(
            f'The user was identified as: {first_response.text}. '
            'Now check their permissions using the permissions tool.'
        ),
        tools=['get_user_permissions'],
        context={'user': {'id': input.user_id}},
    )

    return f'User info: {first_response.text}\nPermissions: {second_response.text}'


async def main() -> None:
    pass


if __name__ == '__main__':
    ai.run_main(main())

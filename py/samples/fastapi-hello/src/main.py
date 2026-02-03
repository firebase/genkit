# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""BugBot: AI Code Reviewer.

    genkit start -- uv run src/main.py
    curl localhost:8080/review -d '{"code": "query = f\"SELECT * FROM users WHERE id={user_input}\""}'

If something looks wrong, check localhost:4000 to see what the model actually received.
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from genkit import Genkit, Input, Output
from genkit.ai._runtime import RuntimeManager
from genkit.ai._server import ServerSpec
from genkit.core.reflection import create_reflection_asgi_app
from genkit.plugins.google_genai import GoogleAI  # pyright: ignore[reportMissingImports,reportUnknownVariableType]

load_dotenv()

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.0-flash',
    prompt_dir=Path(__file__).parent.parent / 'prompts',
)


# =============================================================================
# Reflection Server for Dev UI (only in dev mode)
# =============================================================================


def _find_free_port(start: int = 3100, end: int = 3999) -> int:
    """Find a free port in the given range."""
    import socket

    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f'No free port found in range {start}-{end}')


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start reflection server for Dev UI integration."""
    reflection_server = None
    runtime_manager = None

    # Only start reflection server in dev mode
    if os.environ.get('GENKIT_ENV') == 'dev':
        port = _find_free_port()
        server_spec = ServerSpec(scheme='http', host='127.0.0.1', port=port)

        # Create and start reflection server
        reflection_app = create_reflection_asgi_app(registry=ai.registry)
        config = uvicorn.Config(reflection_app, host='127.0.0.1', port=port, log_level='warning')
        reflection_server = uvicorn.Server(config)

        # Register runtime with Dev UI using RuntimeManager
        runtime_manager = RuntimeManager(server_spec)
        await runtime_manager.__aenter__()

        # Start reflection server in background
        asyncio.create_task(reflection_server.serve())
        print(f'Genkit reflection server running at {server_spec.url}')

    yield

    # Cleanup
    if reflection_server:
        reflection_server.should_exit = True
    if runtime_manager:
        await runtime_manager.__aexit__(None, None, None)


# =============================================================================
# Models
# =============================================================================

Severity = Literal['critical', 'warning', 'info']
Category = Literal['security', 'bug', 'style']


class Issue(BaseModel):
    """A single issue found in the code."""

    line: int = Field(description='Line number where the issue occurs')
    title: str = Field(description='Brief title like "SQL Injection Risk"')
    severity: Severity
    category: Category
    explanation: str = Field(description='Why this is a problem')
    suggestion: str = Field(description='How to fix it')


class Analysis(BaseModel):
    """Analysis result containing found issues."""

    issues: list[Issue] = Field(default_factory=list)


class CodeInput(BaseModel):
    """Input for code analysis."""

    code: str
    language: str = 'python'


class DiffInput(BaseModel):
    """Input for diff analysis."""

    diff: str
    context: str = ''


# =============================================================================
# Typed Prompt Handles (defined once, reused everywhere)
# =============================================================================

security_prompt = ai.prompt(
    'analyze_security', input=Input(schema=CodeInput), output=Output(schema=Analysis)
)
bugs_prompt = ai.prompt(
    'analyze_bugs', input=Input(schema=CodeInput), output=Output(schema=Analysis)
)
style_prompt = ai.prompt(
    'analyze_style', input=Input(schema=CodeInput), output=Output(schema=Analysis)
)
diff_prompt = ai.prompt(
    'analyze_diff', input=Input(schema=DiffInput), output=Output(schema=Analysis)
)


# =============================================================================
# Flows
# =============================================================================


@ai.flow()
async def analyze_security(input: CodeInput) -> Analysis:
    """Analyze code for security vulnerabilities."""
    response = await security_prompt(input=input)
    return response.output


@ai.flow()
async def analyze_bugs(input: CodeInput) -> Analysis:
    """Analyze code for potential bugs."""
    response = await bugs_prompt(input=input)
    return response.output


@ai.flow()
async def analyze_style(input: CodeInput) -> Analysis:
    """Analyze code for style issues."""
    response = await style_prompt(input=input)
    return response.output


@ai.flow()
async def review_code(input: CodeInput) -> Analysis:
    """Run all analyzers in parallel and combine results."""
    security, bugs, style = await asyncio.gather(
        analyze_security(input),
        analyze_bugs(input),
        analyze_style(input),
    )
    return Analysis(issues=security.issues + bugs.issues + style.issues)


@ai.flow()
async def review_diff(input: DiffInput) -> Analysis:
    """Review a code diff for issues."""
    response = await diff_prompt(input=input)
    return response.output


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(title='BugBot', description='AI-powered code review API', lifespan=lifespan)


@app.post('/review')
async def review(code: str, language: str = 'python') -> Analysis:
    """Review code for security, bugs, and style issues."""
    return await review_code(CodeInput(code=code, language=language))


@app.post('/review/security')
async def review_security_endpoint(code: str, language: str = 'python') -> Analysis:
    """Review code for security issues only."""
    return await analyze_security(CodeInput(code=code, language=language))


@app.post('/review/diff')
async def review_diff_endpoint(diff: str, context: str = '') -> Analysis:
    """Review a code diff."""
    return await review_diff(DiffInput(diff=diff, context=context))


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)

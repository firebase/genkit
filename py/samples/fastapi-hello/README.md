# FastAPI Hello - BugBot Code Reviewer

A FastAPI application demonstrating Genkit's typed prompts and Dev UI integration.

## Features

- **Typed Prompts**: Python Pydantic types as the single source of truth for schemas
- **Dev UI Integration**: Full Genkit Developer UI support for debugging
- **Parallel Analysis**: Security, bugs, and style analysis run concurrently

## Quick Start

```bash
# Set your API key
export GEMINI_API_KEY=your-key-here

# Run with Genkit Dev UI
genkit start -- uv run src/main.py
```

Then open:
- **API**: http://localhost:8080
- **Dev UI**: http://localhost:4000

## API Endpoints

```bash
# Full code review (security + bugs + style)
curl -X POST "http://localhost:8080/review?code=your_code_here"

# Security analysis only
curl -X POST "http://localhost:8080/review/security?code=your_code_here"

# Diff review
curl -X POST "http://localhost:8080/review/diff?diff=your_diff_here"
```

## Key Concepts

1. **Python-First Schemas**: Define types in Python, schemas auto-generated
2. **Dotprompt Files**: Templates separate from code, just `output.format: json`
3. **Typed Outputs**: `response.output` returns Pydantic instances, not dicts

# Built-in Middleware Examples

Minimal examples of Genkit's built-in middleware.

## Quick Start

```bash
GEMINI_API_KEY=your-key uv run python src/main.py
```

## Middleware Available

| Middleware | Use Case |
|------------|----------|
| `retry()` | Exponential backoff on transient failures |
| `fallback()` | Try alternative models on failure |
| `download_request_media()` | Download HTTP media URLs and convert to base64 data URIs |
| `validate_support()` | Reject unsupported requests early (auto-injected) |
| `simulate_system_prompt()` | Convert system messages for incompatible models (auto-injected) |
| `augment_with_context()` | Inject RAG docs into prompts (auto-injected) |

## Examples

### Retry
```python
await ai.generate(
    prompt='Hello',
    use=[retry(max_retries=3, initial_delay_ms=1000)]
)
```

### Fallback
```python
await ai.generate(
    prompt='Hello',
    use=[fallback(ai, models=['backup-model'])]
)
```

### Download Media
```python
await ai.generate(
    prompt=[
        "What's in this image?",
        Part(root=MediaPart(media=Media(url="https://example.com/image.png")))
    ],
    use=[download_request_media(max_bytes=10_000_000)]
)
```

### Combined
```python
await ai.generate(
    prompt='Hello',
    use=[
        retry(max_retries=2),
        fallback(ai, models=['backup-model']),
    ]
)
```

### Custom
```python
async def my_middleware(req, ctx, next_fn):
    # before
    response = await next_fn(req, ctx)
    # after
    return response

await ai.generate(prompt='Hello', use=[my_middleware])
```

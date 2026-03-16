# FastAPI BugBot

Code review API — security, bugs, style. FastAPI + Genkit with streaming.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
genkit start -- uv run src/main.py
```

- API: http://localhost:8080
- Swagger: http://localhost:8080/docs
- Dev UI: http://localhost:4000

```bash
curl -X POST http://localhost:8080/review \
  -H "Content-Type: application/json" \
  -d '{"code": "eval(user_input)", "language": "python"}'
```

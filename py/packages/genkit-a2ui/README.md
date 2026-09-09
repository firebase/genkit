# genkit-a2ui

Experimental [A2UI](https://a2ui.org/) middleware for Genkit Python.

Add `A2ui()` to `use=[...]` on `ai.generate` or `define_agent`. The model may
emit ` ```a2ui ` fences; the middleware rewrites them into
`application/a2ui+json` data parts. On the next turn, those parts become text
again so the model can see prior surfaces and button clicks.

```python
from genkit import Genkit
from genkit_a2ui import A2ui, envelopes_from_parts
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()])

response = await ai.generate(
    model='googleai/gemini-2.5-flash',
    prompt='Show me the weather in Tokyo',
    use=[A2ui()],
)
envelopes = envelopes_from_parts(response.message.content)
```

> Status: experimental.

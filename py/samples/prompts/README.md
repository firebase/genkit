# Prompts

Learn how `.prompt` files work with templates, variants, helpers, and streaming. [Docs](https://genkit.dev/docs/dotprompt).

```bash
export GEMINI_API_KEY=your-api-key
uv sync
uv run src/main.py
```

To inspect the flows in Dev UI instead:

```bash
genkit start -- uv run src/main.py
```

Try `generate_recipe`, `generate_recipe_with_pro_preview`, `generate_recipe_with_pro_preview_customtools`, `generate_robot_recipe`, and `tell_story`.
This sample uses `googleai/gemini-3.1-flash-lite-preview` by default and includes explicit Gemini 3.1 Pro Preview flows.

# Google Media

Three focused Google media examples: text-to-speech, Imagen image generation, and Veo video generation.

```bash
export GEMINI_API_KEY=your-api-key
uv sync
uv run src/main.py
```

To explore the flows in Dev UI instead:

```bash
genkit start -- uv run src/main.py
```

Flows: `generate_speech`, `generate_image`, `generate_video`, `generate_video_veo31`, `generate_video_veo31_fast`, `generate_video_veo30`, `generate_video_veo30_fast`.

`generate_video` is configured for Dev UI testing of these Google AI Veo models:

- `googleai/veo-3.1-generate-preview`
- `googleai/veo-3.1-fast-generate-preview`
- `googleai/veo-3.0-generate-001`
- `googleai/veo-3.0-fast-generate-001`

The flow input includes Veo config fields such as `aspect_ratio`, `duration_seconds`, `resolution`, and `seed`.

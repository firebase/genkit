# Google Vertex Imagen

Generate images from text via Vertex AI Imagen. Uses GCP creds, not `GEMINI_API_KEY`.

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud auth application-default login
uv sync
uv run src/main.py
```

To explore it in Dev UI instead:

```bash
genkit start -- uv run src/main.py
```

Run `draw_image_with_imagen`, `summarize_with_gemini_31_pro`, and `rewrite_with_gemini_31_flash_lite`.

Note: Gemini 3.1 preview flows use the Vertex plugin's global routing fallback.

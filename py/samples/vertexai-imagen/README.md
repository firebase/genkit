# Google Vertex Imagen

Generate images from text via Vertex AI Imagen. Uses GCP creds, not `GEMINI_API_KEY`.

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
gcloud auth application-default login
uv sync
genkit start -- uv run src/main.py
```

Dev UI at http://localhost:4000. Run `draw_image_with_imagen`.

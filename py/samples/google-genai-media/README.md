# Google Media

TTS, Imagen, Veo, Lyria. Text-to-speech, images, video, music.

```bash
# Simulated (no key)
uv sync && genkit start -- uv run src/main.py

# Real models
export GEMINI_API_KEY=your-api-key
genkit start -- uv run src/main.py
```

Lyria needs Vertex: `export GOOGLE_CLOUD_PROJECT=...` and `gcloud auth application-default login`.

Flows: `tts_speech_generator`, `imagen_image_generator`, `gemini_image_generator`, `lyria_audio_generator`, `veo_video_generator`.

# Google Gemini Image Generation

This sample uses the Gemini API for image generation. This sample uses the
experimental Gemini model, which is available for now only in the Gemini API,
not in Vertex AI api. If you need to run it on Vertex AI, please, refer to
the Imagen sample.

Prerequisites:
* The `genkit` package.

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

To run this sample:

1. Install the `genkit` package.
2. Set the `GEMINI_API_KEY` environment variable to your Gemini API key.

```bash
export GEMINI_API_KEY=<Your api key>
```

### Monitoring and Running

For an enhanced development experience, use the provided `run.sh` script to start the sample with automatic reloading:

```bash
./run.sh
```

This script uses `watchmedo` to monitor changes in:
- `src/` (Python logic)
- `../../packages` (Genkit core)
- `../../plugins` (Genkit plugins)
- File patterns: `*.py`, `*.prompt`, `*.json`

Changes will automatically trigger a restart of the sample. You can also pass command-line arguments directly to the script, e.g., `./run.sh --some-flag`.

## Run the sample

TODO

```bash
uv run src/main.py
```

## Testing This Demo

1. **Prerequisites**:
   ```bash
   export GEMINI_API_KEY=your_api_key
   ```
   Or the demo will prompt for the key interactively.

2. **Run the demo**:
   ```bash
   cd py/samples/google-genai-image
   ./run.sh
   ```

3. **Open DevUI** at http://localhost:4000

4. **Test image generation**:
   - [ ] `draw_image_with_gemini` - Generate an image from text
   - [ ] `generate_images` - Multi-modal image generation
   - [ ] Check output is a valid image (data URI)

5. **Test image description**:
   - [ ] `describe_image_with_gemini` - Describe an input image
   - [ ] Verify description matches image content

6. **Test image editing**:
   - [ ] `gemini_image_editing` - Edit/modify existing images

7. **Test video** (Veo):
   - [ ] `photo_move_veo` - Generate video from image
   - [ ] Note: Video generation may take longer

8. **Expected behavior**:
   - Images returned as base64 data URIs
   - Descriptions are accurate to image content
   - Edits preserve context while making changes

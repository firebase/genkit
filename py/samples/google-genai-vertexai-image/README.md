# Google Imagen Image Generation

This sample uses the Vertex API and Imagen model for image generation.
Imagen model is not available with Gemini API. If you need to run image
generation on Gemini API, please, refer to the google-gemini-image sample.

Prerequisites:

* A Google Cloud account with access to VertexAI service.
* The `genkit` package.

To run this sample:

1. Install the `genkit` package.
2. Install [GCP CLI](https://cloud.google.com/sdk/docs/install)
3. Put your GCP project and location in the code to run VertexAI there.
4. Run the sample.

## Run the sample

Use the following command from a sample folder:

```bash
uv run src/google_genai_vertexai_image.py
```

## Available options

The options are based on `genai.types.GenerateImagesConfig` model.

| Option                       | Type    | Description                                                                                                                                  | Available Values                                                                 |
|------------------------------|---------|----------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| `output_gcs_uri`             | string  | Cloud Storage URI used to store the generated images.                                                                                        |                                                                                  |
| `negative_prompt`            | string  | Description of what to discourage in the generated images.                                                                                   |                                                                                  |
| `number_of_images`           | integer | Number of images to generate.                                                                                                                |                                                                                  |
| `guidance_scale`             | float   | Controls how much the model adheres to the text prompt. Large values increase output and prompt alignment, but may compromise image quality. |                                                                                  |
| `seed`                       | integer | Random seed for image generation. This is not available when `add_watermark` is set to true.                                                 |                                                                                  |
| `safety_filter_level`        |         | Filter level for safety filtering.                                                                                                           | `BLOCK_LOW_AND_ABOVE`, `BLOCK_MEDIUM_AND_ABOVE`, `BLOCK_ONLY_HIGH`, `BLOCK_NONE` |
| `person_generation`          |         | Allows generation of people by the model.                                                                                                    | `DONT_ALLOW`, `ALLOW_ADULT`, `ALLOW_ALL`                                         |
| `include_safety_attributes`  | bool    | Whether to report the safety scores of each image in the response.                                                                           |                                                                                  |
| `include_rai_reason`         | bool    | Whether to include the Responsible AI filter reason if the image is filtered out of the response.                                            |                                                                                  |
| `language`                   |         | Language of the text in the prompt.                                                                                                          | `auto`, `en`, `ja`, `ko`, `hi`                                                   |
| `output_mime_type`           | string  | MIME type of the generated image.                                                                                                            |                                                                                  |
| `output_compression_quality` | integer | Compression quality of the generated image (for `image/jpeg` only).                                                                          |                                                                                  |
| `add_watermark`              | bool    | Whether to add a watermark to the generated images.                                                                                          |                                                                                  |
| `aspect_ratio`               | string  | Aspect ratio of the generated images.                                                                                                        |                                                                                  |
| `enhance_prompt`             | bool    | Whether to use the prompt rewriting logic.                                                                                                   |                                                                                  |

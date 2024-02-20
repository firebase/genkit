import {
  modelRef,
  modelAction,
  GenerationRequest,
  CandidateData,
} from '@google-genkit/ai/model';
import { PluginOptions } from '.';
import z from 'zod';
import { GoogleAuth } from 'google-auth-library';

const ImagenConfigSchema = z.object({
  /** Language of the prompt text. */
  language: z
    .enum(['auto', 'en', 'es', 'hi', 'ja', 'ko', 'pt', 'zh-TW', 'zh', 'zh-CN'])
    .optional(),
  /** Desired aspect ratio of output image. */
  aspectRatio: z.enum(['1:1', '9:16', '16:9']).optional(),
  /** A negative prompt to help generate the images. For example: "animals" (removes animals), "blurry" (makes the image clearer), "text" (removes text), or "cropped" (removes cropped images). */
  negativePrompt: z.string().optional(),
  /** Any non-negative integer you provide to make output images deterministic. Providing the same seed number always results in the same output images. Accepted integer values: 1 - 2147483647. */
  seed: z.number().optional(),
});
type ImagenConfig = z.infer<typeof ImagenConfigSchema>;

export const imagen2 = modelRef({
  name: 'vertex-ai/imagen2',
  info: {
    label: 'Vertex AI - Imagen2',
    supports: {
      media: false,
      multiturn: false,
      tools: false,
      output: ['media'],
    },
  },
  configSchema: ImagenConfigSchema,
});

function endpoint(options: PluginOptions) {
  // eslint-disable-next-line max-len
  return `https://${options.location}-aiplatform.googleapis.com/v1/projects/${options.projectId}/locations/${options.location}/publishers/google/models/imagegeneration@005:predict`;
}

function extractText(request: GenerationRequest) {
  return request.messages
    .at(-1)!
    .content.map((c) => c.text || '')
    .join('');
}

function toParameters(request: GenerationRequest) {
  const config = request.config?.custom || ({} as ImagenConfig);

  const out = {
    sampleCount: request.candidates || 1,
    aspectRatio: config.aspectRatio,
    negativePrompt: config.negativePrompt,
    seed: config.seed,
    language: config.language,
  };

  for (const k in out) {
    if (!out[k]) delete out[k];
  }

  return out;
}

function extractPromptImage(request: GenerationRequest): string | undefined {
  return request.messages
    .at(-1)
    ?.content.find((p) => !!p.media)
    ?.media?.url.split(',')[1];
}

interface PredictionResponse {
  predictions: { bytesBase64Encoded: string; mimeType: string }[];
}

export function imagen2Model(client: GoogleAuth, options: PluginOptions) {
  return modelAction(imagen2, async (request) => {
    const fetch = (await import('node-fetch')).default;
    // TODO: Don't do it this way.
    const accessToken = await (
      await client.getApplicationDefault()
    ).credential.getAccessToken();

    const instance: Record<string, any> = {
      prompt: extractText(request),
    };
    if (extractPromptImage(request))
      instance.image = { bytesBase64Encoded: extractPromptImage(request) };

    const req: any = {
      instances: [instance],
      parameters: toParameters(request),
    };

    const response = await fetch(endpoint(options), {
      method: 'POST',
      body: JSON.stringify(req),
      headers: {
        Authorization: `Bearer ${accessToken.token}`,
        'Content-Type': 'application/json',
        'User-Agent': 'genkit',
      },
    });

    if (response.status !== 200) {
      throw new Error(
        `Error from Imagen2: HTTP ${response.status}: ${await response.text()}`
      );
    }

    const responseBody: PredictionResponse =
      (await response.json()) as PredictionResponse;

    const candidates: CandidateData[] = responseBody.predictions.map((p, i) => {
      const b64data = p.bytesBase64Encoded;
      const mimeType = p.mimeType;
      return {
        index: i,
        finishReason: 'stop',
        message: {
          role: 'model',
          content: [
            {
              media: {
                url: `data:${mimeType};base64,${b64data}`,
                contentType: mimeType,
              },
            },
          ],
        },
      };
    });
    return {
      candidates,
      usage: { custom: { generations: candidates.length } },
      custom: responseBody,
    };
  });
}

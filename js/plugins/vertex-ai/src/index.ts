import { Plugin, genkitPlugin } from '@genkit-ai/common/config';
import { imagen2, imagen2Model } from './imagen';
import {
  geminiModel,
  geminiPro,
  geminiProVision,
  SUPPORTED_GEMINI_MODELS,
} from './gemini';
import { VertexAI } from '@google-cloud/vertexai';
import { getProjectId } from '@genkit-ai/common';
import { textEmbeddingGeckoEmbedder, textembeddingGecko } from './embedder';
import { GoogleAuth } from 'google-auth-library';

export { imagen2, geminiPro, geminiProVision, textembeddingGecko };

export interface PluginOptions {
  projectId?: string;
  location: string;
}

export const vertexAI: Plugin<[PluginOptions]> = genkitPlugin(
  'vertex-ai',
  async (options: PluginOptions) => {
    const authClient = new GoogleAuth();
    const vertexClient = new VertexAI({
      project: options.projectId || getProjectId(),
      location: options.location,
    });
    return {
      models: [
        imagen2Model(authClient, options),
        ...Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
          geminiModel(name, vertexClient)
        ),
      ],
      embedders: [textEmbeddingGeckoEmbedder(authClient, options)],
    };
  }
);

export default vertexAI;

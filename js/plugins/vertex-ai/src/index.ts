import { Plugin, genkitPlugin } from '@genkit-ai/common/config';
import { imagen2, imagen2Model } from './imagen';
import {
  geminiModel,
  geminiPro,
  geminiProVision,
  SUPPORTED_GEMINI_MODELS,
} from './gemini';
import { VertexAI } from '@google-cloud/vertexai';
import { getProjectId, getLocation } from '@genkit-ai/common';
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
    const project = options.projectId || getProjectId();
    const location = options.location || getLocation();

    const confError = (parameter: string, envVariableName: string) => {
      return new Error(
        `VertexAI Plugin is missing the '${parameter}' environment variable. Please set the '${envVariableName}' environment variable or explicitly pass '${parameter}' into genkit.conf.ts.`
      );
    };
    if (!location) {
      throw confError(project, 'GCLOUD_LOCATION');
    }
    if (!project) {
      throw confError(project, 'GCLOUD_PROJECT');
    }

    const vertexClient = new VertexAI({ project, location });
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

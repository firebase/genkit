import { Plugin, genkitPlugin } from '@google-genkit/common/config';
import { imagen2, imagen2Model } from './imagen';
import {
  geminiModel,
  geminiPro,
  geminiProVision,
  SUPPORTED_GEMINI_MODELS,
} from './gemini';
import { GoogleAuth } from 'google-auth-library';
export { imagen2, geminiPro, geminiProVision };

export interface PluginOptions {
  projectId?: string;
  location: string;
}

export const vertexAI: Plugin<[PluginOptions]> = genkitPlugin(
  'vertex-ai',
  (options: PluginOptions) => {
    const authClient = new GoogleAuth();

    return {
      models: [
        imagen2Model(authClient, options),
        ...Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
          geminiModel(name, options)
        ),
      ],
    };
  }
);

export default vertexAI;

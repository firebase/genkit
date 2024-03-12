import { Plugin, genkitPlugin } from '@genkit-ai/common/config';
import {
  googleAIModel,
  geminiPro,
  geminiProVision,
  SUPPORTED_MODELS,
} from './gemini';
export { geminiPro, geminiProVision };

export interface PluginOptions {
  apiKey: string;
}

export const googleGenAI: Plugin<[string] | []> = genkitPlugin(
  'google-ai',
  async (apiKey?: string) => {
    return {
      models: [
        ...Object.keys(SUPPORTED_MODELS).map((name) =>
          googleAIModel(name, apiKey)
        ),
      ],
    };
  }
);

export default googleGenAI;

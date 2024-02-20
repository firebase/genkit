import { Plugin, genkitPlugin } from '@google-genkit/common/config';
import { imagen2, imagen2Model } from './imagen';
import { GoogleAuth } from 'google-auth-library';
export { imagen2 };

export interface PluginOptions {
  projectId?: string;
  location: string;
}

export const vertexAI: Plugin<[PluginOptions]> = genkitPlugin(
  'vertex-ai',
  (options: PluginOptions) => {
    const authClient = new GoogleAuth();

    return {
      models: [imagen2Model(authClient, options)],
    };
  }
);

export default vertexAI;

import { EmbedderArgument } from '@genkit-ai/ai/embedder';
import * as aiplatform from '@google-cloud/aiplatform';
import { GoogleAuth } from 'google-auth-library';
import z from 'zod';
import { PluginOptions } from '..';

export type MakeRequired<T, K extends keyof T> = T & {
  [P in K]-?: T[P];
};

//  this internal interface will be passed to the vertexIndexers and vertexRetrievers functions
export interface vertexVectorSearchOptions<
  EmbedderCustomOptions extends z.ZodTypeAny,
> {
  pluginOptions: PluginOptions;
  authClient: GoogleAuth;
  defaultEmbedder: EmbedderArgument<EmbedderCustomOptions>;
}

export type IIndexDatapoint =
  aiplatform.protos.google.cloud.aiplatform.v1.IIndexDatapoint;

export class Datapoint extends aiplatform.protos.google.cloud.aiplatform.v1
  .IndexDatapoint {
  constructor(properties: IIndexDatapoint) {
    super(properties);
  }
}

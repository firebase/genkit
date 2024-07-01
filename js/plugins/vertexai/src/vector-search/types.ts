import { EmbedderArgument } from '@genkit-ai/ai/embedder';
import * as aiplatform from '@google-cloud/aiplatform';
import { GoogleAuth } from 'google-auth-library';
import z from 'zod';
import { PluginOptions } from '..';

export type MakeRequired<T, K extends keyof T> = T & {
  [P in K]-?: T[P];
};

// This internal interface will be passed to the vertexIndexers and vertexRetrievers functions
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

export type IFindNeighborsRequest =
  aiplatform.protos.google.cloud.aiplatform.v1.IFindNeighborsRequest;
export type IFindNeighborsResponse =
  aiplatform.protos.google.cloud.aiplatform.v1.IFindNeighborsResponse;
export type ISparseEmbedding =
  aiplatform.protos.google.cloud.aiplatform.v1.IndexDatapoint.ISparseEmbedding;
export type IRestriction =
  aiplatform.protos.google.cloud.aiplatform.v1.IndexDatapoint.IRestriction;
export type INumericRestriction =
  aiplatform.protos.google.cloud.aiplatform.v1.IndexDatapoint.INumericRestriction;

// Define the Zod schema for ISparseEmbedding
const SparseEmbeddingSchema = z.object({
  values: z.array(z.number()).optional(),
  dimensions: z.array(z.union([z.number(), z.string()])).optional(),
});

// Define the Zod schema for IRestriction
const RestrictionSchema = z.object({
  namespace: z.string().optional(),
  allowList: z.array(z.string()).optional(),
  denyList: z.array(z.string()).optional(),
});

// Define the Zod schema for INumericRestriction
const NumericRestrictionSchema = z.object({
  valueInt: z.union([z.number(), z.string()]).optional(),
  valueFloat: z.number().optional(),
  valueDouble: z.number().optional(),
  namespace: z.string().optional(),
  op: z
    .union([
      z.enum([
        'OPERATOR_UNSPECIFIED',
        'LESS',
        'LESS_EQUAL',
        'EQUAL',
        'GREATER_EQUAL',
        'GREATER',
        'NOT_EQUAL',
      ]),
      z.null(),
    ])
    .optional(),
});

// Define the Zod schema for ICrowdingTag
const CrowdingTagSchema = z.object({
  crowdingAttribute: z.string().optional(),
});

// Define the Zod schema for IIndexDatapoint
const IndexDatapointSchema = z.object({
  datapointId: z.string().optional(),
  featureVector: z.array(z.number()).optional(),
  sparseEmbedding: SparseEmbeddingSchema.optional(),
  restricts: z.array(RestrictionSchema).optional(),
  numericRestricts: z.array(NumericRestrictionSchema).optional(),
  crowdingTag: CrowdingTagSchema.optional(),
});

// Define the Zod schema for INeighbor
export const NeighborSchema = z.object({
  datapoint: IndexDatapointSchema.optional(),
  distance: z.number().optional(),
  sparseDistance: z.number().optional(),
});

export type Neighbor = z.infer<typeof NeighborSchema>;

// Define the Zod schema for INearestNeighbors
const NearestNeighborsSchema = z.object({
  id: z.string().optional(),
  neighbors: z.array(NeighborSchema).optional(),
});

// Define the Zod schema for IFindNeighborsResponse
const findNeighborsResponseSchema = z.object({
  nearestNeighbors: z.array(NearestNeighborsSchema).optional(),
});

// TypeScript types for Zod schemas
type IndexDatapoint = z.infer<typeof IndexDatapointSchema>;
type FindNeighborsResponse = z.infer<typeof findNeighborsResponseSchema>;

// Function to assert type equality
function assertTypeEquality<T>(value: T): void {}

// Asserting type equality
assertTypeEquality<IIndexDatapoint>({} as IndexDatapoint);
assertTypeEquality<IFindNeighborsResponse>({} as FindNeighborsResponse);

export { findNeighborsResponseSchema };

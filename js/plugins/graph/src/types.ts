import { JsonSchema7ObjectType } from "zod-to-json-schema";
import z from "zod";
import { SerializedGraph } from "graphology-types";
import { DirectedGraph } from "graphology";
import { Flow } from "@genkit-ai/flow";

export type FlowGraph = DirectedGraph<
  FlowGraphNodeAttributes,
  FlowGraphEdgeAttributes
>;

export type SerializedFlowGraph = SerializedGraph<
  FlowGraphNodeAttributes,
  FlowGraphEdgeAttributes
>;

export type FlowGraphNodeAttributes = {
  name: string;
  inputValues: Record<string, any>;
  outputValues?: Record<string, any>;
  flow?: Flow<any, any, any>;
  schema?: {
    inputSchema: {
      zod?: z.ZodSchema<any>;
      jsonSchema: JsonSchema7ObjectType;
    };
    outputSchema: {
      zod?: z.ZodSchema<any>;
      jsonSchema: JsonSchema7ObjectType;
    };
  };
};

export type FlowGraphEdgeAttributes = {
  includeKeys: string[];
};
const AttributesSchema = z.record(z.any());

export const FlowGraphNodeAttributesSchema = z.object({
  name: z.string(),
  inputValues: z.record(z.any()),
  outputValues: z.record(z.any()).optional(),
  flow: z.any().optional(),
  schema: z
    .object({
      inputSchema: z.object({
        zod: z.any().optional(),
        jsonSchema: z.object({}).optional(),
      }),
      outputSchema: z.object({
        zod: z.any().optional(),
        jsonSchema: z.object({}).optional(),
      }),
    })
    .optional(),
});

export const FlowGraphEdgeAttributesSchema = z.object({
  includeKeys: z.array(z.string()),
});

const GraphTypeSchema = z.union([
  z.literal("mixed"),
  z.literal("directed"),
  z.literal("undirected"),
]);

const GraphOptionsSchema = z.object({
  allowSelfLoops: z.boolean().optional(),
  multi: z.boolean().optional(),
  type: GraphTypeSchema.optional(),
});

const SerializedNodeSchema = z.object({
  key: z.string(),
  attributes: FlowGraphNodeAttributesSchema.optional(),
});

const SerializedEdgeSchema = z.object({
  key: z.string().optional(),
  source: z.string(),
  target: z.string(),
  attributes: FlowGraphEdgeAttributesSchema.optional(),
  undirected: z.boolean().optional(),
});

export const SerializedFlowGraphSchema = z.object({
  attributes: AttributesSchema,
  options: GraphOptionsSchema,
  nodes: z.array(SerializedNodeSchema),
  edges: z.array(SerializedEdgeSchema),
});

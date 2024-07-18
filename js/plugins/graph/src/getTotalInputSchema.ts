/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import z, { UnknownKeysParam, util, ZodObject, ZodRawShape } from 'zod';
import { JsonSchema7ObjectType } from 'zod-to-json-schema';
import { FlowGraph } from './types';
export function addSubschema<
  T extends ZodRawShape,
  UnknownKeys extends 'strip' | 'passthrough' | 'strict',
>(
  totalSchema: ZodObject<T, UnknownKeys, any>,
  schema: ZodObject<T, UnknownKeys, any>,
  subschemaName: string,
  keys: string[]
) {
  // Create the mask object for the pick method
  const pickMask = Object.fromEntries(
    keys.map((key) => [key, true])
  ) as util.Exactly<{ [k in keyof T]?: true }, T>;

  // Pick the specified keys from the schema using the mask
  const pickSchema = schema.pick(pickMask);

  // Create a new object schema with the picked schema under the subschemaName
  const subschema = z.object({
    [subschemaName]: pickSchema,
  });

  // Merge the new subschema with the total schema
  return totalSchema.merge(subschema);
}

export const getInputZodSchema = (graph: FlowGraph, node: string) => {
  const schema = graph.getNodeAttributes(node).schema;

  if (!schema || !schema.inputSchema.zod) {
    throw new Error(`Node ${node} does not have a zod schema attribute`);
  }

  return schema.inputSchema.zod as ZodObject<ZodRawShape, UnknownKeysParam>;
};

export const getOutputZodSchema = (graph: FlowGraph, node: string) => {
  const schema = graph.getNodeAttributes(node).schema;

  if (!schema || !schema.outputSchema.zod) {
    throw new Error(`Node ${node} does not have a zod schema attribute`);
  }

  return schema.outputSchema.zod as ZodObject<ZodRawShape, UnknownKeysParam>;
};

export const getInputJsonSchema = (graph: FlowGraph, node: string) => {
  const schema = graph.getNodeAttributes(node).schema;

  if (!schema || !schema.inputSchema.jsonSchema) {
    throw new Error(`Node ${node} does not have a json schema attribute`);
  }
  return schema.inputSchema.jsonSchema;
};

export const getOutputJsonSchema = (graph: FlowGraph, node: string) => {
  const schema = graph.getNodeAttributes(node).schema;

  if (!schema || !schema.outputSchema.jsonSchema) {
    throw new Error(`Node ${node} does not have a json schema attribute`);
  }
  return schema.outputSchema.jsonSchema as JsonSchema7ObjectType;
};

export const getTotalInputsSchema = (graph: FlowGraph) => {
  const nodes = graph.nodes();

  let totalInputSchema = z.object({});

  for (const node of nodes) {
    const inEdges = graph.inEdges(node);

    console.log('inEdges', inEdges);

    const inputKeys = graph
      .inEdges(node)
      .map((edge) => graph.getEdgeAttributes(edge))
      .flatMap((a) => a.includeKeys);

    const inputJsonSchema = getInputJsonSchema(graph, node);

    const keysWithoutInputsPiped = Object.keys(
      inputJsonSchema.properties
    ).filter((key) => !inputKeys.includes(key));

    const inputSchema = getInputZodSchema(graph, node);

    if (keysWithoutInputsPiped.length > 0) {
      totalInputSchema = addSubschema(
        totalInputSchema,
        inputSchema,
        node,
        keysWithoutInputsPiped
      );
    }
  }
  return totalInputSchema;
};

export const getTotalOutputSchema = (graph: FlowGraph) => {
  const nodes = graph.nodes();

  let totalOutputSchema = z.object({});

  for (const node of nodes) {
    const outputKeys = graph
      .outEdges(node)
      .map((edge) => graph.getEdgeAttributes(edge))
      .flatMap((a) => a.includeKeys);

    const outputJsonSchema = getOutputJsonSchema(graph, node);

    const keysWithoutOutputsPiped = Object.keys(
      outputJsonSchema.properties
    ).filter((key) => !outputKeys.includes(key));

    const outputSchema = getOutputZodSchema(graph, node);

    totalOutputSchema = addSubschema(
      totalOutputSchema,
      outputSchema,
      node,
      keysWithoutOutputsPiped
    );
  }
  return totalOutputSchema;
};

export const getTotalOutput = (graph: FlowGraph) => {
  const nodes = graph.nodes();

  let totalOutput = {};

  for (const node of nodes) {
    const outputKeys = graph
      .outEdges(node)
      .map((edge) => graph.getEdgeAttributes(edge))
      .flatMap((a) => a.includeKeys);

    const outputJsonSchema = getOutputJsonSchema(graph, node);

    const keysWithoutOutputsPiped = Object.keys(
      outputJsonSchema.properties
    ).filter((key) => !outputKeys.includes(key));

    console.log('keysWithoutOutputsPiped', node, keysWithoutOutputsPiped);

    const outputValues = graph.getNodeAttributes(node).outputValues;

    for (const key of keysWithoutOutputsPiped) {
      if (outputValues && outputValues.hasOwnProperty(key)) {
        totalOutput = {
          ...totalOutput,
          [node]: {
            ...totalOutput[node],
            [key]: outputValues[key],
          },
        };
      }
    }
  }
  console.log('totalOutput', totalOutput);
  return totalOutput;
};

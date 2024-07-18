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

import { runFlow } from '@genkit-ai/flow';
import { FlowGraph } from './types';

export const runGraph = async (order: string[], graph: FlowGraph) => {
  // Process each node according to the execution order
  for (const node of order) {
    const attributes = graph.getNodeAttributes(node);
    const { inputValues, flow } = attributes;

    if (!flow) {
      throw new Error(`Flow not found during execution: ${node}`);
    }

    // Execute the flow associated with the node and get output values
    let outputValues: Record<string, string | number> = {};

    for (let i = 0; i < 4; i++) {
      if (i === 4) {
        throw new Error('Retry limit exceeded');
      }
      try {
        console.log('inputValues', JSON.stringify(inputValues, null, 2));

        outputValues = await runFlow(flow, inputValues);
        break;
      } catch (error) {
        console.error(`Error in node ${node}:`, error, 'Retrying...');
      }
    }

    graph.setNodeAttribute(node, 'outputValues', outputValues);

    // Distribute output values to connected nodes
    const outgoingEdges = graph.outEdges(node);
    for (const edge of outgoingEdges) {
      const edgeAttributes = graph.getEdgeAttributes(edge);

      const { includeKeys } = edgeAttributes;
      const targetInputValues = distributeValues(
        includeKeys as string[],
        outputValues
      );

      // Merge new values into the target node's input values
      const targetAttributes = graph.getTargetAttributes(edge);
      const target = graph.target(edge);
      graph.setNodeAttribute(target, 'inputValues', {
        ...targetAttributes.inputValues,
        ...targetInputValues,
      });
    }

    console.log(`Processed node: ${node}`);
  }
};

function distributeValues(
  checkedKeys: string[],
  outputValues: Record<string, string | number>
) {
  // Filter and map values to pass along based on checked keys
  return Object.fromEntries(
    checkedKeys
      .map((key) => [key, outputValues[key]])
      .filter(([_k, value]) => value !== undefined)
  );
}

const retry = async <T>(fn: () => Promise<T>, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      console.error(`Error in retry ${i}:`, error);
    }
  }
  throw new Error('Retry limit exceeded');
};

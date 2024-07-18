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

import { genkitPlugin, Plugin } from '@genkit-ai/core';
import {
  defineFlow as originalDefineFlow,
  Flow,
  runFlow,
  StepsFunction,
} from '@genkit-ai/flow';
import bodyParser from 'body-parser';
import cors, { CorsOptions } from 'cors';
import express from 'express';

import {
  FlowGraph,
  SerializedFlowGraph,
  SerializedFlowGraphSchema,
} from './types';

import Graph, { DirectedGraph } from 'graphology';
import { hasCycle, topologicalSort } from 'graphology-dag';
import z from 'zod';
import zodToJsonSchema, { JsonSchema7ObjectType } from 'zod-to-json-schema';
import {
  findGenkitComposeFile,
  findGenkitComposeFileSync,
  parseAsGraph,
  readAndParseConfigFile,
  readAndParseConfigFileSync,
} from './getComposeConfig';
import {
  getTotalInputsSchema,
  getTotalOutput,
  getTotalOutputSchema,
} from './getTotalInputSchema';
import { runGraph } from './runGraph';
interface GraphPluginParams {
  port?: number;
  cors?: CorsOptions;
}

const CREATED_FLOWS = 'genkitx-graph__CREATED_FLOWS';
const CREATED_EDGES = 'genkitx-graph__CREATED_EDGES';

function createdFlows(): Flow<any, any, any>[] {
  if (global[CREATED_FLOWS] === undefined) {
    global[CREATED_FLOWS] = [];
  }
  return global[CREATED_FLOWS];
}

function createdEdges(): {
  source: string;
  target: string;
  attributes: { includeKeys: string[] };
}[] {
  if (global[CREATED_EDGES] === undefined) {
    global[CREATED_EDGES] = [];
  }
  return global[CREATED_EDGES];
}

export function defineEdge(
  flow1: Flow<any, any, any>,
  flow2: Flow<any, any, any>,
  includeKeys: string[]
) {
  createdEdges().push({
    source: flow1.name,
    target: flow2.name,
    attributes: {
      includeKeys,
    },
  });
}

export function defineFlow<
  I extends z.AnyZodObject = z.AnyZodObject,
  O extends z.AnyZodObject = z.AnyZodObject,
  S extends z.AnyZodObject = z.AnyZodObject,
>(
  config: {
    name: string;
    inputSchema: I;
    outputSchema: O;
    streamSchema?: S;
  },
  steps: StepsFunction<I, O, S>
): Flow<I, O, S> {
  const flow = originalDefineFlow(config, steps);

  createdFlows().push(flow);

  return flow;
}

export const graph: Plugin<[GraphPluginParams]> = genkitPlugin(
  'graph',
  async (params: GraphPluginParams) => {
    const app = getAppSync({
      port: params.port,
      cors: params.cors,
    });

    app.listen(params.port, () => {
      console.log(`Graph plugin listening at http://localhost:${params.port}`);
    });

    if (process.env.GENKIT_ENV === 'dev') {
      return {};
    }
  }
);

function defaultGraph() {
  const graph: FlowGraph = new DirectedGraph();
  for (const flow of createdFlows()) {
    graph.addNode(flow.name, {
      name: flow.name,
      inputValues: {},
      flow: flow,
      schema: {
        inputSchema: {
          zod: flow.inputSchema,
          jsonSchema: zodToJsonSchema(
            flow.inputSchema
          ) as JsonSchema7ObjectType,
        },
        outputSchema: {
          zod: flow.outputSchema,
          jsonSchema: zodToJsonSchema(
            flow.outputSchema
          ) as JsonSchema7ObjectType,
        },
      },
    });
  }

  for (const edge of createdEdges()) {
    console.log('adding edge', edge);
    graph.addDirectedEdge(edge.source, edge.target, edge.attributes);
  }
  return graph;
}

interface ComposeServerParams {
  port?: number;
  cors?: CorsOptions;
  composeConfigPath?: string;
}

export const getApp = async (params: ComposeServerParams) => {
  const app = express();
  app.use(bodyParser.json());
  if (params?.cors) {
    app.use(cors(params.cors));
  }

  const composeConfigPath =
    params.composeConfigPath || (await findGenkitComposeFile());

  if (!composeConfigPath) {
    throw new Error('No compose config file found');
  }

  const composeConfig = await readAndParseConfigFile(composeConfigPath);

  const graph = parseAsGraph(composeConfig);
  const flows = createdFlows();

  for (const node of graph.nodes()) {
    const flow = flows.find((flow) => flow.name === node);
    if (!flow) {
      throw new Error(`Flow not found: ${node}`);
    }
    graph.setNodeAttribute(node, 'flow', flow);
    graph.setNodeAttribute(node, 'schema', {
      inputSchema: {
        zod: flow.inputSchema,
        jsonSchema: zodToJsonSchema(flow.inputSchema) as JsonSchema7ObjectType,
      },
      outputSchema: {
        zod: flow.outputSchema,
        jsonSchema: zodToJsonSchema(flow.outputSchema) as JsonSchema7ObjectType,
      },
    });
  }

  if (hasCycle(graph)) {
    throw new Error('The flow diagram contains a cycle.');
  }

  validateNoDuplicates(graph);

  const totalInputSchema = getTotalInputsSchema(graph);
  const totalOutputSchema = getTotalOutputSchema(graph);

  const executionOrder = topologicalSort(graph);

  app.post('/runTotalFlow', async (req, res) => {
    let totalFlowInputValues: z.infer<typeof totalInputSchema> = {};

    try {
      totalFlowInputValues = totalInputSchema.parse(req.body);
    } catch (error) {
      console.error(error);
      res.status(400).send('Invalid input values');
      return;
    }

    Object.entries(totalFlowInputValues).forEach(([node, values]) => {
      graph.setNodeAttribute(
        node,
        'inputValues',
        values as Record<string, any>
      );
    });

    await runGraph(executionOrder, graph);

    const totalOutputValues = getTotalOutput(graph);

    try {
      totalOutputSchema.parse(totalOutputValues);
    } catch (error) {
      console.error(error);
      res.status(500).send('Invalid output values');
      return;
    }
    res.send(totalOutputValues);
  });

  app.post('/runGraph', async (req, res) => {
    const parsedBody = SerializedFlowGraphSchema.parse(
      req.body
    ) as SerializedFlowGraph;

    const graph = Graph.from(parsedBody);

    if (hasCycle(graph)) {
      throw new Error('The flow diagram contains a cycle.');
    }

    try {
      validateNoDuplicates(graph);
    } catch (error) {
      res.status(400).send('Duplicate keys found in piping.');
    }

    const executionOrder = topologicalSort(graph);

    runGraph(executionOrder, graph);

    res.send(graph.toJSON());
  });

  app.get('/introspect', (req, res) => {
    res.send(zodToJsonSchema(totalInputSchema));
  });

  return app;
};

export const getAppSync = (params: ComposeServerParams) => {
  const app = express();
  app.use(bodyParser.json());
  if (params?.cors) {
    app.use(cors(params.cors));
  }

  const composeConfigPath =
    params.composeConfigPath || findGenkitComposeFileSync();

  const composeConfig = composeConfigPath
    ? readAndParseConfigFileSync(composeConfigPath)
    : null;

  const graph = composeConfig ? parseAsGraph(composeConfig) : defaultGraph();

  const flows = createdFlows();

  for (const node of graph.nodes()) {
    const flow = flows.find((flow) => flow.name === node);
    if (!flow) {
      throw new Error(`Flow not found: ${node}`);
    }
    graph.setNodeAttribute(node, 'flow', flow);
    graph.setNodeAttribute(node, 'schema', {
      inputSchema: {
        zod: flow.inputSchema,
        jsonSchema: zodToJsonSchema(flow.inputSchema) as JsonSchema7ObjectType,
      },
      outputSchema: {
        zod: flow.outputSchema,
        jsonSchema: zodToJsonSchema(flow.outputSchema) as JsonSchema7ObjectType,
      },
    });
  }

  if (hasCycle(graph)) {
    throw new Error('The flow diagram contains a cycle.');
  }

  validateNoDuplicates(graph);

  const totalInputSchema = getTotalInputsSchema(graph);
  const totalOutputSchema = getTotalOutputSchema(graph);

  const executionOrder = topologicalSort(graph);

  const totalFlow = originalDefineFlow(
    {
      name: 'totalFlow',
      inputSchema: totalInputSchema,
      outputSchema: totalOutputSchema,
    },
    async (input) => {
      Object.entries(input).forEach(([node, values]) => {
        graph.setNodeAttribute(
          node,
          'inputValues',
          values as Record<string, any>
        );
      });

      await runGraph(executionOrder, graph);

      const totalOutputValues = getTotalOutput(graph);

      return totalOutputValues;
    }
  );

  app.post('/runTotalFlow', async (req, res) => {
    let totalFlowInputValues: z.infer<typeof totalInputSchema> = {};

    try {
      totalFlowInputValues = totalInputSchema.parse(req.body);
    } catch (error) {
      console.error(error);
      res.status(400).send('Invalid input values');
      return;
    }

    const totalOutputValues = await runFlow(totalFlow, totalFlowInputValues);

    try {
      totalOutputSchema.parse(totalOutputValues);
    } catch (error) {
      console.error(error);
      res.status(500).send('Invalid output values');
      return;
    }
    res.send(totalOutputValues);
  });

  app.post('/runGraph', async (req, res) => {
    const parsedBody = SerializedFlowGraphSchema.parse(
      req.body
    ) as SerializedFlowGraph;

    const graph = Graph.from(parsedBody);

    for (const node of parsedBody.nodes) {
      const flow = createdFlows().find((f) => f.name === node.attributes?.name);

      const schema = {
        inputSchema: {
          zod: flow?.inputSchema,
          jsonSchema: zodToJsonSchema(
            flow?.inputSchema
          ) as JsonSchema7ObjectType,
        },
        outputSchema: {
          zod: flow?.outputSchema,
          jsonSchema: zodToJsonSchema(
            flow?.outputSchema
          ) as JsonSchema7ObjectType,
        },
      };

      graph.updateNodeAttributes(node.key, (a) => ({
        ...a,
        flow,
        schema,
      }));
    }

    if (hasCycle(graph)) {
      throw new Error('The flow diagram contains a cycle.');
    }

    try {
      validateNoDuplicates(graph);
    } catch (error) {
      res.status(400).send('Duplicate keys found in piping.');
    }

    const executionOrder = topologicalSort(graph);

    await runGraph(executionOrder, graph);

    res.send(graph.toJSON());
  });

  app.get('/listFlows', (req, res) => {
    const flows = createdFlows();

    const serializedFlows = flows.map((f) => ({
      name: f.name,
      id: f.name,
      inputSchema: zodToJsonSchema(f.inputSchema),
      outputSchema: zodToJsonSchema(f.outputSchema),
    }));

    res.send(serializedFlows);
  });

  return app;
};

export const validateNoDuplicates = (graph: FlowGraph) => {
  const nodes = graph.nodes();

  for (const node of nodes) {
    const inputKeys = graph
      .inEdges(node)
      .map((edge) => graph.getEdgeAttributes(edge))
      .flatMap((a) => a.includeKeys);

    const keyWithDuplicate = inputKeys.find(
      (key) => inputKeys.filter((k) => k === key).length > 1
    );

    if (keyWithDuplicate) {
      throw new Error(
        `Duplicate key ${keyWithDuplicate} found in input piping for node ${node}`
      );
    }
  }
};

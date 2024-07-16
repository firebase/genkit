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

import { Flow, FlowAuthPolicy, runFlow } from '@genkit-ai/flow';
import express from 'express';
import * as z from 'zod';

export function defineGraph<
  StateSchema extends z.ZodTypeAny = z.ZodTypeAny,
  OutputSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(config: {
  name: string;
  stateSchema?: StateSchema;
  initialState: z.infer<StateSchema>;
  outputSchema?: OutputSchema;
  authPolicy?: FlowAuthPolicy<StateSchema>;
  middleware?: express.RequestHandler[];
}): Graph<StateSchema, OutputSchema> {
  return new Graph(config);
}

const StateReturnSchema = <T extends z.ZodTypeAny>(stateSchema: T) => {
  return z.object({
    state: stateSchema,
    nextNode: z.string(),
  });
};
type StateReturnSchema<T extends z.ZodTypeAny> = ReturnType<
  typeof StateReturnSchema<T>
>;

const EndReturnSchema = <T extends z.ZodTypeAny>(outputSchema: T) => {
  return z.function().args(outputSchema);
};

type EndReturnSchema<T extends z.ZodTypeAny> = ReturnType<
  typeof EndReturnSchema<T>
>;

class Graph<
  StateSchema extends z.ZodTypeAny = z.ZodTypeAny,
  OutputSchema extends z.ZodTypeAny = z.ZodTypeAny,
  FlowInputSchema extends StateSchema = StateSchema,
  FlowOutputSchema extends StateReturnSchema<StateSchema> | OutputSchema =
    | StateReturnSchema<StateSchema>
    | OutputSchema,
> {
  readonly name: string;
  readonly stateSchema?: StateSchema;
  readonly outputSchema?: OutputSchema;
  readonly authPolicy?: FlowAuthPolicy<StateSchema>;
  readonly middleware?: express.RequestHandler[];
  nodes: Record<string, Flow<FlowInputSchema, FlowOutputSchema>> = {};
  entrypoint: keyof typeof this.nodes = '';
  state: StateSchema;
  constructor(config: {
    name: string;
    stateSchema?: StateSchema;
    initialState: StateSchema;
    outputSchema?: OutputSchema;
    authPolicy?: FlowAuthPolicy<StateSchema>;
    middleware?: express.RequestHandler[];
  }) {
    this.name = config.name;
    this.outputSchema = config.outputSchema;
    this.state = config.initialState;
    this.authPolicy = config.authPolicy;
    this.middleware = config.middleware;
  }

  addNode(flow: Flow<FlowInputSchema, FlowOutputSchema>) {
    if (this.nodes[flow.name]) {
      throw new Error(`Node ${flow.name} already exists`);
    }

    this.nodes[flow.name] = flow;
  }

  setEntrypoint(name: string) {
    if (!this.nodes[name]) {
      throw new Error(`Node ${name} does not exist`);
    }

    this.entrypoint = name;
  }

  async run(): Promise<z.infer<OutputSchema>> {
    let flowName = this.entrypoint;
    while (true) {
      const result = await runFlow(this.nodes[flowName], this.state);
      let parseResult = this.stateSchema!.safeParse(result);

      if (parseResult.success) {
        this.state = (result as z.infer<StateReturnSchema<StateSchema>>).state!;
        flowName = (result as z.infer<StateReturnSchema<StateSchema>>).nextNode;
        continue;
      }

      parseResult = this.outputSchema!.safeParse(result);

      if (parseResult.success) {
        return result as z.infer<OutputSchema>;
      }
    }
  }
}

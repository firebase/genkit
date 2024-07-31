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

import {
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateSchema,
  FlowStateStore,
  configureGenkit,
} from '@genkit-ai/core';
import { registerFlowStateStore } from '@genkit-ai/core/registry';

export function configureInMemoryStateStore(
  env: string
): InMemoryFlowStateStore {
  configureGenkit({});
  const stateStore = new InMemoryFlowStateStore();
  registerFlowStateStore(env, async () => stateStore);
  return stateStore;
}

export class InMemoryFlowStateStore implements FlowStateStore {
  state: Record<string, string> = {};

  load(id: string): Promise<FlowState | undefined> {
    if (!this.state[id]) {
      return Promise.resolve(undefined);
    }
    return Promise.resolve(FlowStateSchema.parse(JSON.parse(this.state[id])));
  }

  save(id: string, state: FlowState): Promise<void> {
    this.state[id] = JSON.stringify(state);
    return Promise.resolve();
  }

  async list(
    query?: FlowStateQuery | undefined
  ): Promise<FlowStateQueryResponse> {
    return {
      flowStates: Object.values(this.state).map(
        (s) => JSON.parse(s) as FlowState
      ),
    };
  }
}

export function asyncTurn() {
  return new Promise((r) => setTimeout(r, 0));
}

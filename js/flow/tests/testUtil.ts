import {
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateSchema,
  FlowStateStore,
} from '@genkit-ai/common';
import { configureGenkit } from '@genkit-ai/common/config';
import { registerFlowStateStore } from '@genkit-ai/common/registry';

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

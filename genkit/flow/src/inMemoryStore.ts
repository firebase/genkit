import * as registry from '@google-genkit/common/registry';
import { FlowState, FlowStateSchema, FlowStateStore } from './types';

/**
 * Not very useful in pactice in-memory flow state store.
 */
export class InMemoryFlowStateStore implements FlowStateStore {
  private state: Record<string, string> = {};

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
}

export const inMemoryFlowStateStore = new InMemoryFlowStateStore();

/**
 * Sets the global default state store to in-memory store.
 */
export function useInMemoryStateStore() {
  registry.register('/flows/stateStore', inMemoryFlowStateStore);
}

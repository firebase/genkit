import { startReflectionApi } from './reflectionApi';
import { Action } from './types';
import { TraceStore } from './tracing/types';
import { FlowStateStore } from './flowTypes';
import * as z from 'zod';

const __actionRegistry: Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> = {};
const __traceStore: Record<string, TraceStore> = {};
const __flowStateStore: Record<string, FlowStateStore> = {};

/**
 * Type of a runnable action.
 */
export type ActionType =
  | 'chat-llm'
  | 'text-llm'
  | 'retriever'
  | 'indexer'
  | 'embedder'
  | 'flow'
  | 'model';

/**
 * Looks up a registry key (action type and key) in the registry.
 */
export function lookupAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  R extends Action<I, O>
>(key: string): R {
  return __actionRegistry[key] as R;
}

/**
 * Registers an action in the registry.
 */
export function registerAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  type: ActionType,
  id: string,
  action: Action<I, O>
) {
  const key = `/${type}/${id}`;
  if (__actionRegistry.hasOwnProperty(key)) {
    console.log(`WARNING: ${key} already has an entry in the registry.`);
  }
  __actionRegistry[key] = action;
}

/**
 * Returns all actions in the registry.
 */
export function listActions(): Record<
  string,
  Action<z.ZodTypeAny, z.ZodTypeAny>
> {
  return Object.assign({}, __actionRegistry);
}

/**
 * Registers a trace store for the given environment.
 */
export function registerTraceStore(env: string, traceStore: TraceStore) {
  __traceStore[env] = traceStore;
}

/**
 * Looks up the trace store for the given environment.
 */
export function lookupTraceStore(env: string): TraceStore {
  return __traceStore[env];
}

/**
 * Registers a flow state store for the given environment.
 */
export function registerFlowStateStore(
  env: string,
  flowStateStore: FlowStateStore
) {
  __flowStateStore[env] = flowStateStore;
}

/**
 * Looks up the flow state store for the given environment.
 */
export function lookupFlowStateStore(env: string): FlowStateStore {
  return __flowStateStore[env];
}

/**
 * Development mode only. Starts a Reflection API so that the actions can be called by the Runner.
 */
if (process.env.GENKIT_ENV === 'dev') {
  startReflectionApi();
}

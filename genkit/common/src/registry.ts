import { startReflectionApi } from './reflectionApi';
import { Action, ActionMetadata } from './types';
import * as z from 'zod';

const __actionRegistry = {};
const __registry = {};

/**
 * Type of a runnable action.
 */
export type ActionType =
  | 'chat-llm'
  | 'text-llm'
  | 'retriever'
  | 'embedder'
  | 'flow';

/**
 * Looks up a registry key (action type and key) in the registry.
 */
export function lookupAction<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  R extends Action<I, O>
>(key: string): R {
  return __actionRegistry[key];
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
export function listActions(): Record<string, Action<z.ZodTypeAny, z.ZodTypeAny>> {
  return Object.assign({}, __actionRegistry);
}

// TODO: Remove these once tracing is removed from the registry.

export function register(key: string, subject: any) {
  __registry[key] = subject;
}

export function lookup(key: string): any {
  return __registry[key];
}

/**
 * Development mode only. Starts a Reflection API so that the actions can be called by the Runner.
 */
if (process.env.GENKIT_START_REFLECTION_API) {
  startReflectionApi();
}

import { startReflectionApi } from './reflectionApi';
import { Action, ActionMetadata } from './types';
import * as z from 'zod';

const __actionRegistry = {};
const __registry = {};

export type ActionType =
  | 'chat-llms'
  | 'text-llms'
  | 'retrievers'
  | 'embedders'
  | 'flows';

/**
 * Looks up a registry key (action type and key) in the registry.
 */
export function lookupAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(key: string): Action<I, O> {
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
export function listActions(): { [key: string]: ActionMetadata<z.ZodTypeAny, z.ZodTypeAny> } {
  const actions = {};
  for (const key in __actionRegistry) {
    if (__actionRegistry.hasOwnProperty(key)) {
      actions[key] = __actionRegistry[key].__action;
    }
  }
  return actions;
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
if (process.env.START_REFLECTION_API) {
  startReflectionApi();
}

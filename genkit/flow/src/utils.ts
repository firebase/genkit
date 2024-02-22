import { AsyncLocalStorage } from 'node:async_hooks';
import { Context } from './context.js';
import { v4 as uuidv4 } from 'uuid';
import z from 'zod';

/**
 * Adds flows specific prefix for OpenTelemetry span attributes.
 */
export function metadataPrefix(name: string) {
  return `flow:${name}`;
}

const ctxAsyncLocalStorage = new AsyncLocalStorage<
  Context<z.ZodTypeAny, z.ZodTypeAny>
>();

/**
 * Returns current active context.
 */
export function getActiveContext() {
  return ctxAsyncLocalStorage.getStore();
}

/**
 * Execute the provided function in the flow context. Call {@link getActiveContext()} anywhere
 * within the async call stack to retrieve the context.
 */
export function runWithActiveContext<R>(
  ctx: Context<z.ZodTypeAny, z.ZodTypeAny>,
  fn: () => R
) {
  return ctxAsyncLocalStorage.run(ctx, fn);
}

/**
 * Generates a flow ID.
 */
export function generateFlowId() {
  return uuidv4();
}

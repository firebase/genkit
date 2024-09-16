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

import { AsyncLocalStorage } from 'node:async_hooks';
import { v4 as uuidv4 } from 'uuid';
import z from 'zod';
import { Context } from './context.js';

/**
 * Adds flows specific prefix for OpenTelemetry span attributes.
 */
export function metadataPrefix(name: string) {
  return `flow:${name}`;
}

const ctxAsyncLocalStorage = new AsyncLocalStorage<
  Context<z.ZodTypeAny, z.ZodTypeAny, z.ZodTypeAny>
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
  ctx: Context<z.ZodTypeAny, z.ZodTypeAny, z.ZodTypeAny>,
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

/**
 * Gets the auth object from the current context.
 */
export function getFlowAuth(): any {
  const ctx = getActiveContext();
  if (!ctx) {
    throw new Error('Can only be run from a flow');
  }
  return ctx.auth;
}

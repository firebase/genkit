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

import { Action, Operation } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import * as z from 'zod';
import { PollingConfig } from './context.js';
import {
  FlowExecutionError,
  FlowNotFoundError,
  FlowStillRunningError,
} from './errors.js';
import {
  Flow,
  FlowWrapper,
  RunStepConfig,
  StepsFunction,
  defineFlow,
} from './flow.js';
import { Invoker, Scheduler } from './types.js';
import { getActiveContext } from './utils.js';

/**
 * Defines the durable flow.
 */
export function durableFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  config: {
    name: string;
    inputSchema?: I;
    outputSchema?: O;
    streamSchema?: S;
    invoker?: Invoker<I, O, S>;
    scheduler?: Scheduler<I, O, S>;
  },
  steps: StepsFunction<I, O, S>
): Flow<I, O, S> {
  return defineFlow(
    {
      name: config.name,
      inputSchema: config.inputSchema,
      outputSchema: config.outputSchema,
      streamSchema: config.streamSchema,
      invoker: config.invoker,
      experimentalScheduler: config.scheduler,
      experimentalDurable: true,
    },
    steps
  );
}

/**
 * Schedules a flow run. This is always return an operation that's not completed (done=false).
 */
export async function scheduleFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  payload: z.infer<I>,
  delaySeconds?: number
): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  const state = await flow.invoker(flow, {
    schedule: {
      input: flow.inputSchema ? flow.inputSchema.parse(payload) : payload,
      delay: delaySeconds,
    },
  });
  return state;
}

/**
 * Resumes an interrupted flow.
 */
export async function resumeFlow<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  flowId: string,
  payload: any
): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  return await flow.invoker(flow, {
    resume: {
      flowId,
      payload,
    },
  });
}

/**
 * Returns an operation representing current state of the flow.
 */
export async function getFlowState<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  flowId: string
): Promise<Operation> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  if (!flow.stateStore) {
    throw new Error('Flow state must be configured.');
  }
  const state = await (await flow.stateStore()).load(flowId);
  if (!state) {
    throw new FlowNotFoundError(`flow state ${flowId} not found`);
  }
  const op = {
    ...state.operation,
  } as Operation;
  if (state.blockedOnStep) {
    op.blockedOnStep = state.blockedOnStep;
  }
  return op;
}
/**
 * A flow steap that executes an action with provided input and memoizes the output.
 */
export function runAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  action: Action<I, O>,
  input: z.infer<I>,
  actionConfig?: RunStepConfig
): Promise<z.infer<O>> {
  const config: RunStepConfig = {
    ...actionConfig,
    name: actionConfig?.name || action.__action.name,
  };
  return run(config, input, () => action(input));
}

/**
 * A local utility that waits for the flow execution to complete. If flow errored then a
 * {@link FlowExecutionError} will be thrown.
 */
export async function waitFlowToComplete<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  flow: Flow<I, O, S> | FlowWrapper<I, O, S>,
  flowId: string
): Promise<z.infer<O>> {
  if (!(flow instanceof Flow)) {
    flow = flow.flow;
  }
  let state: Operation | undefined = undefined;
  try {
    state = await getFlowState(flow, flowId);
  } catch (e) {
    logger.error(e);
    // TODO: add timeout
    if (!(e instanceof FlowNotFoundError)) {
      throw e;
    }
  }
  if (state && state?.done) {
    return parseOutput(flowId, state);
  } else {
    await asyncSleep(1000);
    return await waitFlowToComplete(flow, flowId);
  }
}

function parseOutput<O extends z.ZodTypeAny>(
  flowId: string,
  state: Operation
): z.infer<O> {
  if (!state.done) {
    throw new FlowStillRunningError(flowId);
  }
  if (state.result?.error) {
    throw new FlowExecutionError(
      flowId,
      state.result.error,
      state.result.stacktrace
    );
  }
  return state.result?.response;
}

export function run<T>(
  experimentalConfig: RunStepConfig,
  func: () => Promise<T>
): Promise<T>;
export function run<T>(
  experimentalConfig: RunStepConfig,
  input: any | undefined,
  func: () => Promise<T>
): Promise<T>;
export function run<T>(name: string, func: () => Promise<T>): Promise<T>;

/**
 * A flow steap that executes the provided function and memoizes the output.
 */
export function run<T>(
  nameOrConfig: string | RunStepConfig,
  funcOrInput: () => Promise<T>,
  fn?: () => Promise<T>
): Promise<T> {
  let config: RunStepConfig;
  if (typeof nameOrConfig === 'string') {
    config = {
      name: nameOrConfig,
    };
  } else {
    config = nameOrConfig;
  }
  const func = arguments.length === 3 ? fn : funcOrInput;
  const input = arguments.length === 3 ? funcOrInput : undefined;
  if (!func) {
    throw new Error('unable to resolve run function');
  }
  const ctx = getActiveContext();
  if (!ctx) throw new Error('can only be run from a flow');
  return ctx.run(config, input, func);
}

/**
 * Interrupts the flow execution until the flow is resumed with input defined by `responseSchema`.
 */
export function interrupt<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  stepName: string,
  responseSchema: I,
  func?: (payload: z.infer<I>) => Promise<z.infer<O>>
): Promise<z.infer<O>> {
  const ctx = getActiveContext();
  if (!ctx) throw new Error('interrupt can only be run from a flow');
  return ctx.interrupt(
    stepName,
    func || ((input: z.infer<I>): z.infer<O> => input),
    responseSchema
  );
}

/**
 * Interrupts flow execution and resumes it when specified amount if time elapses.
 */
export function sleep(actionId: string, durationMs: number) {
  const ctx = getActiveContext();
  if (!ctx) throw new Error('sleep can only be run from a flow');
  return ctx.sleep(actionId, durationMs);
}

/**
 * Interrupts the flow and periodically check for the flow ID to complete.
 */
export function waitFor(
  stepName: string,
  flow: Flow<z.ZodTypeAny, z.ZodTypeAny, z.ZodTypeAny>,
  flowIds: string[],
  pollingConfig?: PollingConfig
): Promise<Operation[]> {
  const ctx = getActiveContext();
  if (!ctx) throw new Error('waitFor can only be run from a flow');
  return ctx.waitFor({ flow, stepName, flowIds, pollingConfig });
}

export async function asyncSleep(duration: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, duration);
  });
}

import { Action } from '@google-genkit/common';
import * as z from 'zod';
import { RunStepConfig } from './flow';
import { getActiveContext } from './utils';

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
 * A flow steap that executes the provided function and memoizes the output.
 */
export function run<T>(
  config: RunStepConfig,
  func: () => Promise<T>
): Promise<T>;
export function run<T>(
  config: RunStepConfig,
  input: any | undefined,
  func: () => Promise<T>
): Promise<T>;
export function run<T>(name: string, func: () => Promise<T>): Promise<T>;
/**
 *
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
  actionId: string,
  responseSchema: I,
  func?: (payload: z.infer<I>) => Promise<z.infer<O>>
): Promise<z.infer<O>> {
  const ctx = getActiveContext();
  if (!ctx) throw new Error('interrupt can only be run from a flow');
  return ctx.interrupt(
    actionId,
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
export function waitFor<O extends z.ZodTypeAny>(
  actionId: string,
  flowIds: string | string[]
): z.infer<O> {
  const ctx = getActiveContext();
  if (!ctx) throw new Error('waitFor can only be run from a flow');
  return ctx.waitFor(actionId, flowIds);
}

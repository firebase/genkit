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

import { FlowState, FlowStateExecution, Operation } from '@genkit-ai/core';
import { toJsonSchema } from '@genkit-ai/core/schema';
import {
  SPAN_TYPE_ATTR,
  runInNewSpan,
  setCustomMetadataAttribute,
  setCustomMetadataAttributes,
} from '@genkit-ai/core/tracing';
import { logger } from 'firebase-functions/v1';
import { z } from 'zod';
import { InterruptError } from './errors.js';
import { Flow, RunStepConfig } from './flow.js';
import { metadataPrefix } from './utils.js';

/**
 * Context object encapsulates flow execution state at runtime.
 */
export class Context<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  S extends z.ZodTypeAny,
> {
  private seenSteps: Record<string, number> = {};

  constructor(
    readonly flow: Flow<I, O, S>,
    readonly flowId: string,
    readonly state: FlowState,
    readonly auth?: unknown
  ) {}

  private isCached(stepName: string): boolean {
    return this.state.cache.hasOwnProperty(stepName);
  }
  private getCached<T>(stepName: string): T {
    return this.state.cache[stepName].value;
  }
  private updateCachedValue(stepName: string, value: any) {
    this.state.cache[stepName] = value ? { value } : { empty: true };
  }

  private async memoize<T>(
    stepName: string,
    func: () => Promise<T>
  ): Promise<[T, boolean]> {
    if (this.isCached(stepName)) {
      return [this.getCached(stepName), true];
    }
    const value = await func();
    this.updateCachedValue(stepName, value);
    return [value, false];
  }

  async saveState() {
    if (this.flow.stateStore) {
      await (await this.flow.stateStore()).save(this.flowId, this.state);
    }
  }

  // Runs provided function in the current context. The config can specify retry and other behaviors.
  async run<T>(
    config: RunStepConfig,
    input: any | undefined,
    func: () => Promise<T>
  ): Promise<T> {
    return await runInNewSpan(
      {
        metadata: {
          name: config.name,
        },
        labels: {
          [SPAN_TYPE_ATTR]: 'flowStep',
        },
      },
      async (metadata, _, isRoot) => {
        const stepName = this.resolveStepName(config.name);
        setCustomMetadataAttributes({
          [metadataPrefix('stepType')]: 'run',
          [metadataPrefix('stepName')]: config.name,
          [metadataPrefix('resolvedStepName')]: stepName,
        });
        if (input !== undefined) {
          metadata.input = input;
        }
        const [value, wasCached] = isRoot
          ? await this.memoize(stepName, func)
          : [await func(), false];
        if (wasCached) {
          setCustomMetadataAttribute(metadataPrefix('state'), 'cached');
        } else {
          setCustomMetadataAttribute(metadataPrefix('state'), 'run');
          if (value !== undefined) {
            metadata.output = JSON.stringify(value);
          }
        }
        return value;
      }
    );
  }

  private resolveStepName(name: string) {
    if (this.seenSteps[name] !== undefined) {
      this.seenSteps[name]++;
      name += `-${this.seenSteps[name]}`;
    } else {
      this.seenSteps[name] = 0;
    }
    return name;
  }

  // Executes interrupt step in the current context.
  async interrupt<I extends z.ZodTypeAny, O>(
    stepName: string,
    func: (payload: I) => Promise<O>,
    responseSchema: I | null,
    skipCache?: boolean
  ): Promise<O> {
    return await runInNewSpan(
      {
        metadata: {
          name: stepName,
        },
        labels: {
          [SPAN_TYPE_ATTR]: 'flowStep',
        },
      },
      async (metadata) => {
        const resolvedStepName = this.resolveStepName(stepName);
        setCustomMetadataAttributes({
          [metadataPrefix('stepType')]: 'interrupt',
          [metadataPrefix('stepName')]: stepName,
          [metadataPrefix('resolvedStepName')]: resolvedStepName,
        });
        if (!skipCache && this.isCached(resolvedStepName)) {
          setCustomMetadataAttribute(metadataPrefix('state'), 'skipped');
          return this.getCached(resolvedStepName);
        }
        // TODO: refactor this.
        if (this.state.eventsTriggered.hasOwnProperty(resolvedStepName)) {
          let value;
          try {
            value = await func(
              this.state.eventsTriggered[resolvedStepName] as I
            );
          } catch (e) {
            if (e instanceof InterruptError) {
              setCustomMetadataAttribute(metadataPrefix('state'), 'interrupt');
            } else {
              setCustomMetadataAttribute(metadataPrefix('state'), 'error');
            }
            throw e;
          }
          this.state.blockedOnStep = null;
          if (!skipCache) {
            this.updateCachedValue(resolvedStepName, value);
          }
          setCustomMetadataAttribute(metadataPrefix('state'), 'dispatch');
          if (value !== undefined) {
            metadata.output = JSON.stringify(value);
          }
          return value;
        }
        logger.debug('blockedOnStep', resolvedStepName);
        this.state.blockedOnStep = { name: resolvedStepName };
        if (responseSchema) {
          this.state.blockedOnStep.schema = JSON.stringify(
            toJsonSchema({ schema: responseSchema })
          );
        }
        setCustomMetadataAttribute(metadataPrefix('state'), 'interrupted');
        throw new InterruptError();
      }
    );
  }

  // Sleep for the specified number of seconds.
  async sleep<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    stepName: string,
    seconds: number
  ): Promise<O> {
    const resolvedStepName = this.resolveStepName(stepName);
    if (this.isCached(resolvedStepName)) {
      setCustomMetadataAttribute(metadataPrefix('state'), 'skipped');
      return this.getCached(resolvedStepName);
    }

    await this.flow.scheduler(
      this.flow,
      {
        runScheduled: {
          flowId: this.flowId,
        },
      },
      seconds
    );
    this.updateCachedValue(resolvedStepName, undefined);
    return this.interrupt(
      stepName,
      (input: z.infer<I>): z.infer<O> => input,
      null
    );
  }

  /**
   * Wait for the provided flow to complete execution. This will do a poll.
   * Poll will be done with an exponential backoff (configurable).
   */
  async waitFor(opts: {
    flow: Flow<z.ZodTypeAny, z.ZodTypeAny, z.ZodTypeAny>;
    stepName: string;
    flowIds: string[];
    pollingConfig?: PollingConfig;
  }): Promise<Operation[]> {
    const resolvedStepName = this.resolveStepName(opts.stepName);
    if (this.isCached(resolvedStepName)) {
      return this.getCached(resolvedStepName);
    }
    const states = await this.getFlowsOperations(opts.flow, opts.flowIds);
    if (states.includes(undefined)) {
      throw new Error(
        'Unable to resolve flow state for ' +
          opts.flowIds[states.indexOf(undefined)]
      );
    }
    const ops = states.map((s) => s!.operation);
    if (ops.map((op) => op.done).reduce((a, b) => a && b)) {
      // all done.
      this.updateCachedValue(resolvedStepName, states);
      return ops;
    }
    await this.flow.scheduler(
      this.flow,
      {
        runScheduled: {
          flowId: this.flowId,
        },
      },
      opts.pollingConfig?.interval || 5
    );
    throw new InterruptError();
  }

  private async getFlowsOperations(
    flow: Flow<z.ZodTypeAny, z.ZodTypeAny, z.ZodTypeAny>,
    flowIds: string[]
  ): Promise<(FlowState | undefined)[]> {
    return await Promise.all(
      flowIds.map(async (id) => {
        if (!flow.stateStore) {
          throw new Error('Flow state store must be configured');
        }
        return (await flow.stateStore()).load(id);
      })
    );
  }

  /**
   * Returns current active execution state.
   */
  getCurrentExecution(): FlowStateExecution {
    return this.state.executions[this.state.executions.length - 1];
  }
}

export interface PollingConfig {
  // TODO: add more options
  interval: number;
}

import { FlowState, FlowStateExecution, FlowStateStore } from '@google-genkit/common';
import zodToJsonSchema from 'zod-to-json-schema';
import { InterruptError } from './errors';
import { z } from 'zod';
import {
  SPAN_TYPE_ATTR,
  runInNewSpan,
  setCustomMetadataAttribute,
  setCustomMetadataAttributes,
} from '@google-genkit/common/tracing';
import { RunStepConfig } from './flow';
import { metadataPrefix } from './utils';
import { logger } from 'firebase-functions/v1';

/**
 * Context object encapsulates flow execution state at runtime.
 */
export class Context {
  private seenSteps: Record<string, number> = {};

  constructor(
    readonly flowId: string,
    readonly state: FlowState,
    private stateStore: FlowStateStore
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
    await this.stateStore.save(this.flowId, this.state);
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
            metadata.output = value;
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
    responseSchema: I | null
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
        if (this.isCached(resolvedStepName)) {
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
          this.updateCachedValue(resolvedStepName, value);
          setCustomMetadataAttribute(metadataPrefix('state'), 'dispatch');
          if (value !== undefined) {
            metadata.output = value;
          }
          return value;
        }
        logger.debug('blockedOnStep', resolvedStepName);
        this.state.blockedOnStep = { name: resolvedStepName };
        if (responseSchema) {
          this.state.blockedOnStep.schema = JSON.stringify(
            zodToJsonSchema(responseSchema)
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
    seconds: number // eslint-disable-line @typescript-eslint/no-unused-vars
  ): Promise<O> {
    // TODO: placeholder, enqueue delayed message...
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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async waitFor(stepName: string, flowIds: string | string[]) {
    // TODO: enqueue delayed message, interrupt...
  }

  /**
   * Returns current active execution state.
   */
  getCurrentExecution(): FlowStateExecution {
    return this.state.executions[this.state.executions.length - 1];
  }
}

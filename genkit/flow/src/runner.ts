import {
  FlowError,
  FlowInvokeEnvelopeMessage,
  FlowState,
  FlowStateStore,
  WorkflowDispatcher,
} from './types';
import { z } from 'zod';
import {
  SPAN_TYPE_ATTR,
  newTrace,
  setCustomMetadataAttribute,
} from '@google-genkit/common/tracing';
import { Context } from './context';
import { InterruptError, getErrorMessage, getErrorStack } from './errors';
import { metadataPrefix, runWithActiveContext } from './utils';

type StepsFunction<I extends z.ZodTypeAny, O extends z.ZodTypeAny> = (
  input: z.infer<I>
) => Promise<z.infer<O>>;

/**
 * Runs the flow, manages execution context and state.
 */
export class FlowRunner<I extends z.ZodTypeAny, O extends z.ZodTypeAny> {
  readonly name: string;
  readonly input: I;
  readonly output: O;
  readonly steps: StepsFunction<I, O>;
  // Visible for emulator.
  stateStore: FlowStateStore;
  readonly dispatcher: WorkflowDispatcher<I, O>;

  constructor(config: {
    name: string;
    input: I;
    output: O;
    stateStore: FlowStateStore;
    steps: StepsFunction<I, O>;
    dispatcher: WorkflowDispatcher<I, O>;
  }) {
    this.name = config.name;
    this.input = config.input;
    this.output = config.output;
    this.stateStore = config.stateStore;
    this.steps = config.steps;
    this.dispatcher = config.dispatcher;
  }

  // TODO: make it private. It's used by `startFlowAsync`, but it should be doing it differently.
  createNewState(flowId: string, req: FlowInvokeEnvelopeMessage) {
    return {
      flowId: flowId,
      name: this.name,
      startTime: Date.now(),
      input: req.input,
      cache: {},
      eventsTriggered: {},
      blockedOnStep: null,
      executions: [
        {
          startTime: Date.now(),
          traceIds: [],
        },
      ],
      operation: {
        name: flowId,
        done: false,
      },
    };
  }

  /**
   * Executes the flow with the input in the envelope format.
   */
  async run(req: FlowInvokeEnvelopeMessage): Promise<FlowState> {
    let ctx: Context | undefined = undefined;
    try {
      if (req.flowId) {
        // TODO: refactor me... this is a mess!
        const flowId = req.flowId;
        let state: FlowState;
        let dispatchType;
        if (req.input) {
          // First time, create new state.
          state = this.createNewState(flowId, req);
          dispatchType = 'input';
          ctx = new Context(flowId, state, this.stateStore);
        } else {
          dispatchType = 'retry';
          const retrievedState = await this.stateStore.load(flowId);
          if (retrievedState === undefined) {
            throw new Error("couldn't find flow state for " + flowId);
          }
          state = retrievedState;
          state.executions.push({
            startTime: Date.now(),
            traceIds: [],
          });
          ctx = new Context(flowId, state, this.stateStore);
        }

        // Recived resume event, add to state.
        if (req.resume) {
          dispatchType = 'resume';
          if (!state.blockedOnStep) {
            throw new Error(
              "Unable to resume flow that's currently not interrupted"
            );
          }
          state.eventsTriggered[state.blockedOnStep.name] = req.resume.payload;
        }

        // TODO: add wake up for sleep.
        await this.runSteps(ctx, this.steps, dispatchType);
        return state;
      }
    } catch (e) {
      // special InterruptError exception which interrups the flow when it needs to wait for
      // external stimulus. See `resumeFlow`.
      if (e instanceof InterruptError) {
        console.log('flow interupted, waiting for input');
        return ctx!.state;
      }
      console.log(e);
      // TODO: retry.
      throw e;
    } finally {
      if (ctx) {
        await ctx.saveState();
      }
    }
    return ctx!.state;
  }

  // TODO: refactor me... this is a mess!
  private async runSteps(
    ctx: Context,
    handler: StepsFunction<I, O>,
    dispatchType: string
  ) {
    await runWithActiveContext(ctx, async () => {
      let traceContext;
      if (ctx.state.traceContext) {
        traceContext = JSON.parse(ctx.state.traceContext);
      }
      let errored = false;
      const output = await newTrace(
        {
          name: ctx.flowId,
          labels: {
            [SPAN_TYPE_ATTR]: 'flow',
          },
          links: [{ context: traceContext }],
        },
        async (metadata, rootSpan) => {
          setCustomMetadataAttribute(metadataPrefix('id'), ctx.flowId);
          ctx
            .getCurrentExecution()
            .traceIds.push(rootSpan.spanContext().traceId);
          // Save the trace in the state so that we can tie subsequent invocation together.
          if (!traceContext) {
            ctx.state.traceContext = JSON.stringify(rootSpan.spanContext());
          }
          setCustomMetadataAttribute(
            metadataPrefix('dispatchType'),
            dispatchType
          );
          try {
            const input = this.input
              ? this.input.parse(ctx.state.input)
              : ctx.state.input;
            metadata.input = input;
            const output = await handler(input);
            metadata.output = output;
            metadata.state = 'success';
            setCustomMetadataAttribute(metadataPrefix('state'), 'done');
            return output;
          } catch (e) {
            if (e instanceof InterruptError) {
              setCustomMetadataAttribute(
                metadataPrefix('state'),
                'interrupted'
              );
            } else {
              metadata.state = 'error';
              setCustomMetadataAttribute(metadataPrefix('state'), 'error');
              ctx.state.operation.done = true;
              ctx.state.operation.result = {
                error: getErrorMessage(e),
                stacktrace: getErrorStack(e),
              } as FlowError;
            }
            errored = true;
          }
        }
      );
      if (!errored) {
        // flow done, set response.
        ctx.state.operation.done = true;
        ctx.state.operation.result = { response: output };
      }
    });
  }
}

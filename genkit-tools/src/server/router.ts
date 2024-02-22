import { initTRPC } from '@trpc/server';
import { Runner } from '../runner/runner';
import { Action } from '../types/action';
import * as apis from '../types/apis';

const t = initTRPC.create();

// eslint-disable-next-line @typescript-eslint/explicit-function-return-type
export const TOOLS_SERVER_ROUTER = (runner: Runner) =>
  t.router({
    /** Retrieves all runnable actions. */
    listActions: t.procedure.query(
      async (): Promise<Record<string, Action>> => {
        return runner.listActions();
      }
    ),

    /** Runs an action. */
    runAction: t.procedure
      .input(apis.RunActionRequestSchema)
      .mutation(async ({ input }) => {
        return runner.runAction(input);
      }),

    /** Retrieves all traces for a given environment (e.g. dev or prod). */
    listTraces: t.procedure
      .input(apis.ListTracesRequestSchema)
      .query(async ({ input }) => {
        return runner.listTraces(input);
      }),

    /** Retrieves a trace for a given ID. */
    getTrace: t.procedure
      .input(apis.GetTraceRequestSchema)
      .query(async ({ input }) => {
        return runner.getTrace(input);
      }),

    /** Retrieves all flow states for a given environment (e.g. dev or prod). */
    listFlowStates: t.procedure
      .input(apis.ListFlowStatesRequestSchema)
      .query(async ({ input }) => {
        return runner.listFlowStates(input);
      }),

    /** Retrieves a flow state for a given ID. */
    getFlowState: t.procedure
      .input(apis.GetFlowStateRequestSchema)
      .query(async ({ input }) => {
        return runner.getFlowState(input);
      }),
  });

export type ToolsServerRouter = ReturnType<typeof TOOLS_SERVER_ROUTER>;

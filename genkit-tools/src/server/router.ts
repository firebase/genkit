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
import { initTRPC, TRPCError } from '@trpc/server';
import { EvalRunSchema, LocalFileEvalStore } from '../eval';
import { Runner } from '../runner/runner';
import { GenkitToolsError } from '../runner/types';
import { Action } from '../types/action';
import { AnalyticsInfoSchema } from '../types/analytics';
import * as apis from '../types/apis';
import * as evals from '../types/eval';
import { getAnalyticsSettings } from '../utils/analytics';

const t = initTRPC.create({
  errorFormatter(opts) {
    const { shape, error } = opts;
    if (!(error.cause instanceof GenkitToolsError)) {
      return shape;
    }
    return {
      ...shape,
      data: {
        ...shape.data,
        genkitErrorMessage: (error.cause.data as Record<string, unknown>)
          .message,
        genkitErrorDetails: (error.cause.data as Record<string, unknown>)
          .details,
      },
    };
  },
});

// TODO make this a singleton provider instead
const evalStore = new LocalFileEvalStore();

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

    /** Retrieves all eval run keys */
    listEvalRunKeys: t.procedure
      .input(evals.ListEvalKeysRequestSchema)
      .output(evals.ListEvalKeysResponseSchema)
      .query(async ({ input }) => {
        const response = await evalStore.list(input);
        return {
          evalRunKeys: response.results,
        };
      }),

    /** Retrieves a single eval run by ID */
    getEvalRun: t.procedure
      .input(evals.GetEvalRunRequestSchema)
      .output(EvalRunSchema)
      .query(async ({ input }) => {
        const parts = input.name.split('/');
        const evalRunId = parts[3];
        const actionId = parts[1] !== '-' ? parts[1] : undefined;
        const evalRun = await evalStore.load(evalRunId, actionId);
        if (!evalRun) {
          throw new TRPCError({
            code: 'NOT_FOUND',
            message: `Eval run with ${input.name} not found`,
          });
        }
        return evalRun;
      }),

    /** Gets analytics session information */
    getAnalyticsSettings: t.procedure
      .output(AnalyticsInfoSchema)
      .query(() => getAnalyticsSettings()),
  });

export type ToolsServerRouter = ReturnType<typeof TOOLS_SERVER_ROUTER>;

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

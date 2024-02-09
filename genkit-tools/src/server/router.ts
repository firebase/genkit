import { initTRPC, TRPCError } from '@trpc/server';
import axios from 'axios';
import { Action } from '../types/action';
import * as apis from '../types/apis';
import { FlowState } from '../types/flow';
import { TraceData } from '../types/trace';

const t = initTRPC.create();
const REFLECTION_PORT = process.env.GENKIT_REFLECTION_PORT || 3100;
const REFLECTION_API_URL = `http://localhost:${REFLECTION_PORT}/api`;

export const TOOLS_SERVER_ROUTER = t.router({
  /** Retrieves all runnable actions. */
  listActions: t.procedure.query(async (): Promise<Record<string, Action>> => {
    try {
      const response = await axios.get(`${REFLECTION_API_URL}/actions`);
      if (response.status !== 200) {
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Failed to fetch actions.',
        });
      }
      return response.data as Record<string, Action>;
    } catch (error) {
      console.error('Error fetching actions:', error);
      throw new TRPCError({
        code: 'INTERNAL_SERVER_ERROR',
        message: 'Error fetching actions.',
      });
    }
  }),

  /** Runs an action. */
  runAction: t.procedure
    .input(apis.RunActionRequestSchema)
    .mutation(async ({ input }) => {
      const request: apis.RunActionRequest = {
        key: input.key,
        input: input.input,
      };
      try {
        const response = await axios.post(
          `${REFLECTION_API_URL}/runAction`,
          request,
          {
            headers: {
              'Content-Type': 'application/json',
            },
          },
        );
        // TODO: Improve the error handling here including invalid arguments from the frontend.
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: 'Failed to run action.',
          });
        }
        return response.data as unknown;
      } catch (error) {
        console.error('Error running action:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error running action.',
        });
      }
    }),

  /** Retrieves all traces for a given environment (e.g. dev or prod). */
  listTraces: t.procedure
    .input(apis.ListTracesRequestSchema)
    .query(async ({ input }) => {
      const { env } = input;
      try {
        const response = await axios.get(
          `${REFLECTION_API_URL}/envs/${env}/traces`,
        );
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: `Failed to fetch traces from env ${env}.`,
          });
        }
        return response.data as TraceData[];
      } catch (error) {
        console.error('Error fetching traces:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: `Error fetching traces from env ${env}.`,
        });
      }
    }),

  /** Retrieves a trace for a given ID. */
  getTrace: t.procedure
    .input(apis.GetTraceRequestSchema)
    .query(async ({ input }) => {
      const { env, traceId } = input;
      try {
        const response = await axios.get(
          `${REFLECTION_API_URL}/envs/${env}/traces/${traceId}`,
        );
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: `Failed to fetch trace ${traceId} from env ${env}.`,
          });
        }
        return response.data as TraceData;
      } catch (error) {
        console.error(
          `Error fetching trace ${traceId} from env ${env}:`,
          error,
        );
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: `Error fetching trace ${traceId} from env ${env}.`,
        });
      }
    }),

  /** Retrieves all flow states for a given environment (e.g. dev or prod). */
  listFlowStates: t.procedure
    .input(apis.ListFlowStatesRequestSchema)
    .query(async ({ input }) => {
      const { env } = input;
      try {
        const response = await axios.get(
          `${REFLECTION_API_URL}/envs/${env}/flowStates`,
        );
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: `Failed to fetch flows from env ${env}.`,
          });
        }
        return response.data as FlowState[];
      } catch (error) {
        console.error('Error fetching flows:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: `Error fetching flows from env ${env}.`,
        });
      }
    }),

  /** Retrieves a flow state for a given ID. */
  getFlowState: t.procedure
    .input(apis.GetFlowStateRequestSchema)
    .query(async ({ input }) => {
      const { env, flowId } = input;
      try {
        const response = await axios.get(
          `${REFLECTION_API_URL}/envs/${env}/flowStates/${flowId}`,
        );
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: `Failed to fetch flow ${flowId} from env ${env}.`,
          });
        }
        return response.data as FlowState;
      } catch (error) {
        console.error(`Error fetching flow ${flowId} from env ${env}:`, error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: `Error fetching flow ${flowId} from env ${env}.`,
        });
      }
    }),
});

export type ToolsServerRouter = typeof TOOLS_SERVER_ROUTER;

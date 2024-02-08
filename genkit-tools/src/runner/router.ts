import { initTRPC, TRPCError } from '@trpc/server';
import { z } from 'zod';
import { ActionSchema } from '../common/types';
import { TraceData } from '../types/trace';
import { FlowState } from '../types/flow';
import axios from 'axios';

const t = initTRPC.create();
const REFLECTION_PORT = process.env.GENKIT_REFLECTION_PORT || 3100;
const REFLECTION_API_URL = `http://localhost:${REFLECTION_PORT}/api`;

export const RUNNER_ROUTER = t.router({
  // Retrieves all runnable actions.
  actions: t.procedure.query(
    async (): Promise<Record<string, ActionSchema>> => {
      try {
        const response = await axios.get(`${REFLECTION_API_URL}/actions`);
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: 'Failed to fetch actions.',
          });
        }
        return response.data as Record<string, ActionSchema>;
      } catch (error) {
        console.error('Error fetching actions:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error fetching actions.',
        });
      }
    }
  ),

  // Runs an action.
  runAction: t.procedure
    .input(z.object({ key: z.string(), input: z.any().optional() }))
    .mutation(async ({ input }) => {
      try {
        const response = await axios.post(
          `${REFLECTION_API_URL}/runAction`,
          {
            key: input.key,
            // TODO: This will be cleaned up when there is a strongly typed interface (e.g. OpenAPI).
            // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
            input: input.input,
          },
          {
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );
        // TODO: Improve the error handling here including invalid arguments from the frontend.
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: 'Failed to run action.',
          });
        }
        // TODO: This will be cleaned up when there is a strongly typed interface (e.g. OpenAPI).
        // eslint-disable-next-line @typescript-eslint/no-unsafe-return
        return response.data;
      } catch (error) {
        console.error('Error running action:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error running action.',
        });
      }
    }),

  // Retrieves all traces for a given environment (e.g. dev or prod).
  traces: t.procedure
    .input(z.object({ env: z.string() }))
    .query(async ({ input }) => {
      const { env } = input;
      try {
        const response = await axios.get(`${REFLECTION_API_URL}/envs/${env}/traces`);
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

  // Retrieves a trace for a given ID.
  trace: t.procedure
    .input(z.object({ env: z.string(), traceId: z.string() }))
    .query(async ({ input }) => {
      const { env, traceId } = input;
      try {
        const response = await axios.get(`${REFLECTION_API_URL}/envs/${env}/traces/${traceId}`);
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: `Failed to fetch trace ${traceId} from env ${env}.`,
          });
        }
        return response.data as TraceData;
      } catch (error) {
        console.error(`Error fetching trace ${traceId} from env ${env}:`, error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: `Error fetching trace ${traceId} from env ${env}.`,
        });
      }
    }),

  // Retrieves all flow runs for a given environment (e.g. dev or prod).
  flowStates: t.procedure
    .input(z.object({ env: z.string() }))
    .query(async ({ input }) => {
      const { env } = input;
      try {
        const response = await axios.get(`${REFLECTION_API_URL}/envs/${env}/flowStates`);
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

  // Retrieves a flow run for a given ID.
  flowState: t.procedure
    .input(z.object({ env: z.string(), flowId: z.string() }))
    .query(async ({ input }) => {
      const { env, flowId } = input;
      try {
        const response = await axios.get(`${REFLECTION_API_URL}/envs/${env}/flowStates/${flowId}`);
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

export type RunnerRouter = typeof RUNNER_ROUTER;

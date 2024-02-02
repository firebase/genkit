import { initTRPC, TRPCError } from '@trpc/server';
import { z } from 'zod';
import { ActionSchema } from '../common/types';
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
            message: 'Failed to fetch actions',
          });
        }
        return response.data as Record<string, ActionSchema>;
      } catch (error) {
        console.error('Error fetching actions:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error fetching actions',
        });
      }
    },
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
          },
        );
        // TODO: Improve the error handling here including invalid arguments from the frontend.
        if (response.status !== 200) {
          throw new TRPCError({
            code: 'INTERNAL_SERVER_ERROR',
            message: 'Failed to run action',
          });
        }
        // TODO: This will be cleaned up when there is a strongly typed interface (e.g. OpenAPI).
        // eslint-disable-next-line @typescript-eslint/no-unsafe-return
        return response.data;
      } catch (error) {
        console.error('Error running action:', error);
        throw new TRPCError({
          code: 'INTERNAL_SERVER_ERROR',
          message: 'Error running action',
        });
      }
    }),
});

export type RunnerRouter = typeof RUNNER_ROUTER;

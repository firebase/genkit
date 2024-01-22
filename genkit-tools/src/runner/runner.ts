import * as express from 'express';
import { ErrorRequestHandler } from 'express';
import * as trpcExpress from '@trpc/server/adapters/express';
import { initTRPC, TRPCError } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.create();

export const runnerRouter = t.router({
  // Returns all runnable flows.
  flows: t.procedure.query(() => {
    throw new TRPCError({
      code: 'NOT_IMPLEMENTED',
      message: 'This endpoint is not implemented yet.',
    });
  }),
  // Runs a flow.
  runFlow: t.procedure.input(z.object({ id: z.string() })).mutation(() => {
    throw new TRPCError({
      code: 'NOT_IMPLEMENTED',
      message: 'This endpoint is not implemented yet.',
    });
  }),
  // Reloads all code.
  reload: t.procedure
    .input(z.object({ name: z.string().optional() }).optional())
    .mutation(() => {
      throw new TRPCError({
        code: 'NOT_IMPLEMENTED',
        message: 'This endpoint is not implemented yet.',
      });
    }),
});

export type RunnerRouter = typeof runnerRouter;

export function startRunner(): void {
  const app = express();
  app.use(express.json());
  const errorHandler: ErrorRequestHandler = (err, req, res) => {
    console.error((err as { stack: string }).stack);
    res.status(500).send(err);
  };
  app.use(errorHandler);
  const PORT = process.env['PORT'] || 3000;
  app.use(
    '/api',
    trpcExpress.createExpressMiddleware({
      router: runnerRouter,
    }),
  );
  app.listen(PORT, () => {
    console.log(`Runner API running on http://localhost:${PORT}/api`);
  });
}

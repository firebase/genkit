import { initTRPC } from '@trpc/server';
import * as z from 'zod';

const t = initTRPC.create();

export const uiEndpointsRouter = t.router({
  echoExample: t.procedure
    .input(z.string())
    .query((opts) => opts.input.toUpperCase()),
});

export type UiApi = typeof uiEndpointsRouter;

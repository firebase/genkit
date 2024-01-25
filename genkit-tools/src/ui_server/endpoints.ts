import { initTRPC } from '@trpc/server';
import * as z from 'zod';
import { FirestoreStub } from '../store/firestore_stub';

const t = initTRPC.create();

const FIRESTORE_STUB = new FirestoreStub();

export const uiEndpointsRouter = t.router({
  echoExample: t.procedure
    .input(z.string())
    .query((opts) => opts.input.toUpperCase()),
  listFlowRuns: t.procedure.query(() => FIRESTORE_STUB.listFlowRuns()),
  getFlowRun: t.procedure
    .input(z.string())
    .query(({ input }) => FIRESTORE_STUB.getFlowRun(input)),
  getTrace: t.procedure
    .input(z.string())
    .query(({ input }) => FIRESTORE_STUB.getTrace(input)),
});

export type UiApi = typeof uiEndpointsRouter;

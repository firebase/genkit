// This is a stub; the Firestore reader will be read from a config file and
// will likely be in the core package. This is for getting the UI work
// unblocked.
// Because it's a stub, ignore a bunch of bad typing:
/* eslint-disable @typescript-eslint/no-unsafe-assignment */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
/* eslint-disable @typescript-eslint/no-explicit-any */

import { StateRetriever } from './state_retriever';
import { Firestore, getFirestore } from 'firebase-admin/firestore';
import { initializeApp } from 'firebase-admin/app';
import { logger } from '../utils/logger';

const COLLECTION = 'ai-flows';

export class FirestoreStub implements StateRetriever {
  private readonly db: Firestore;

  constructor() {
    const app = initializeApp();
    this.db = getFirestore(app);
  }

  async listFlowRuns(): Promise<unknown[]> {
    const q = await this.db
      .collection(COLLECTION)
      .orderBy('startTime', 'desc')
      .limit(20)
      .get();
    return q.docs
      .map((ref) => ref.data())
      .map((f) => ({
        flowId: f.flowId,
        name: f.name,
        startTime: f.startTime,
        status: f.operation.done
          ? f.operation.result.error
            ? 'ERROR'
            : 'SUCCESS'
          : 'RUNNING',
      }));
  }

  async getFlowRun(flowId: string): Promise<unknown> {
    const flow = await this.db.collection(COLLECTION).doc(flowId).get();
    const flowData = flow.data();
    if (!flowData) {
      throw new Error('not found');
    }
    flowData.executions = await Promise.all(
      flowData.executions.map((e: { traceIds: string[] }) =>
        this.getTrace(e.traceIds[0]),
      ),
    );
    return flowData;
  }

  async getTrace(traceId: string): Promise<unknown> {
    // TODO: use trace reader
    const traceQuery = await this.db
      .collection('ai-traces-test')
      .doc(traceId)
      .get();
    const trace = traceQuery.data();
    if (!trace) {
      logger.warn('trace not found: ' + traceId + '. Try reloading.');
      return {};
    }
    let rootSpan;
    Object.values(trace.spans).forEach((span: any) => {
      if (!span.parentSpanId) {
        rootSpan = span;
      } else {
        const parent = trace.spans[span.parentSpanId];
        if (!parent.spans) parent.spans = [];
        parent.spans.push(span);
        parent.spans.sort((a: any, b: any) => a.startTime - b.startTime);
      }
    });
    if (!rootSpan) {
      throw new Error("couldn't find the root span");
    }
    return rootSpan;
  }
}

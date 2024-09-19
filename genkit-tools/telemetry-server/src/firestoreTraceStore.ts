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

import {
  SpanData,
  SpanDataSchema,
  TraceData,
  TraceDataSchema,
} from '@genkit-ai/tools-common';
import { Firestore } from '@google-cloud/firestore';
import { randomUUID } from 'crypto';
import { TraceQuery, TraceQueryResponse, TraceStore } from './types';

const DOC_MAX_SIZE = 1_000_000;

/** Allow customers to set service account credentials via an environment variable. */
interface Credentials {
  client_email?: string;
  private_key?: string;
}

/**
 * Firestore implementation of a trace store.
 */
export class FirestoreTraceStore implements TraceStore {
  readonly db: Firestore;
  readonly collection: string;
  readonly databaseId: string;
  readonly expireAfterDays: number;

  constructor(
    params: {
      collection?: string;
      databaseId?: string;
      projectId?: string;
      expireAfterDays?: number;
      credentials?: Credentials;
    } = {}
  ) {
    this.collection = params.collection || 'genkit-traces';
    this.databaseId = params.databaseId || '(default)';
    this.expireAfterDays = params.expireAfterDays || 14;
    this.db = new Firestore({
      databaseId: this.databaseId,
      ignoreUndefinedProperties: true,
      credentials: params.credentials,
    });
  }

  async save(traceId: string, traceData: TraceData): Promise<void> {
    const expireAt = Date.now() + this.expireAfterDays * 24 * 60 * 60 * 1000;
    const traceInfo = {
      ...traceData,
      expireAt,
      spans: {},
    };
    const start = Date.now();

    const batches = rebatchSpans(traceData);

    let batchWrite = this.db.batch();
    batchWrite.set(
      this.db.collection(this.collection).doc(traceId),
      traceInfo,
      { merge: true }
    );
    batches.forEach((batch) => {
      batchWrite.create(
        this.db
          .collection(this.collection)
          .doc(traceId)
          .collection('spans')
          .doc(randomUUID()),
        {
          expireAt,
          spans: batch,
        }
      );
    });
    await batchWrite.commit();

    console.debug(
      `saved trace ${traceId}, ${Object.keys(traceData.spans).length} span(s) (${Date.now() - start}ms)`
    );
  }

  async load(traceId: string): Promise<TraceData | undefined> {
    const [traceInfo, spanBatches] = await Promise.all([
      this.db.collection(this.collection).doc(traceId).get(),
      this.db
        .collection(this.collection)
        .doc(traceId)
        .collection('spans')
        .get(),
    ]);
    const spans: Record<string, SpanData> = {};
    spanBatches.forEach((batch) => {
      const spansBatch: Record<string, SpanData> = batch.data().spans;
      Object.keys(spansBatch).forEach((key) => {
        spans[key] = SpanDataSchema.parse(spansBatch[key]);
      });
    });
    return TraceDataSchema.parse({
      ...traceInfo.data(),
      spans,
    });
  }

  async list(query?: TraceQuery): Promise<TraceQueryResponse> {
    const limit = query?.limit || 10;
    let fsQuery = this.db
      .collection(this.collection)
      .orderBy('startTime', 'desc');
    if (query?.continuationToken) {
      fsQuery = fsQuery.startAfter(parseInt(query.continuationToken));
    }
    fsQuery = fsQuery.limit(limit);

    const data = await fsQuery.get();
    const lastVisible = data.docs[data.docs.length - 1];
    return {
      traces: data.docs.map((d) => d.data() as TraceData),
      continuationToken:
        data.docs.length === limit
          ? `${lastVisible.data().startTime}`
          : undefined,
    };
  }
}

/**
 * Batches up spans in the trace by size, trying to make sure each batch does not exceed firestore docs size limit.
 * Will truncate span if it's too big to fit into a batch by itself.
 * @internal
 */
export function rebatchSpans(traceData: TraceData): Record<string, SpanData>[] {
  const batches: Record<string, SpanData>[] = [];
  let lastBatchRunningSize = 0;
  for (const span of Object.values(traceData.spans)) {
    let estimatedSpanSize = estimateSpanSize(span);
    if (estimatedSpanSize >= DOC_MAX_SIZE) {
      console.warn(
        `Truncating data for trace ${traceData.traceId} span ${span.spanId}`
      );
      truncateSpanData(span);
      estimatedSpanSize = estimateSpanSize(span);
    }
    if (lastBatchRunningSize + estimatedSpanSize < DOC_MAX_SIZE) {
      // last batch is small enough, keep piling on...
      if (batches.length === 0) {
        batches.push({});
      }
    } else {
      // last batch is too big, start a new one
      batches.push({});
      lastBatchRunningSize = 0;
    }
    lastBatchRunningSize += estimatedSpanSize;
    batches[batches.length - 1][span.spanId] = span;
  }
  return batches;
}

/**
 * Estimates the data size of the span.
 * @internal
 */
function estimateSpanSize(span: SpanData) {
  if (Object.values(span.attributes).length === 0) {
    return 0;
  }
  return Object.values(span.attributes)
    .map((attr: any) => attr.toString().length)
    .reduce((a, b) => a + b);
}

function truncateSpanData(span: SpanData) {
  span.truncated = true;
  // We fisrt see if deleting output does the trick (input might be useful for replayability)
  delete span.attributes['genkit:output'];
  if (estimateSpanSize(span) < DOC_MAX_SIZE) {
    return;
  }
  delete span.attributes['genkit:input'];
  if (estimateSpanSize(span) < DOC_MAX_SIZE) {
    return;
  }
  // Nuclear option... maybe there's a better way? Not very likely though...
  span.attributes = {};
  return;
}

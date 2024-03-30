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

import { Firestore } from '@google-cloud/firestore';
import { randomUUID } from 'crypto';
import { logger } from '../logging.js';
import {
  SpanData,
  SpanDataSchema,
  TraceData,
  TraceDataSchema,
  TraceQuery,
  TraceQueryResponse,
  TraceStore,
} from './types.js';

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
    } = {}
  ) {
    this.collection = params.collection || 'genkit-traces';
    this.databaseId = params.databaseId || '(default)';
    this.expireAfterDays = params.expireAfterDays || 14;
    this.db = new Firestore({
      databaseId: this.databaseId,
      ignoreUndefinedProperties: true,
    });
  }

  async save(traceId: string, traceData: TraceData): Promise<void> {
    const traceInfo = {
      ...traceData,
      expireAt: Date.now() + this.expireAfterDays * 24 * 60 * 60 * 1000,
      spans: {},
    };
    const start = Date.now();
    await this.db
      .collection(this.collection)
      .doc(traceId)
      .set(traceInfo, { merge: true });
    await this.db
      .collection(this.collection)
      .doc(traceId)
      .collection('spans')
      .doc(randomUUID())
      .set({
        spans: traceData.spans,
      });
    logger.debug(
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

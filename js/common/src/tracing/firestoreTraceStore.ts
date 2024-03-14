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

import { App, AppOptions, getApp, initializeApp } from 'firebase-admin/app';
import { Firestore, getFirestore } from 'firebase-admin/firestore';
import {
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
  readonly app: App;
  readonly collection: string;
  readonly databaseId: string;

  constructor(
    params: {
      app?: App;
      collection?: string;
      databaseId?: string;
      projectId?: string;
    } = {}
  ) {
    let app = params.app;
    this.collection = params.collection || 'ai-traces-test';
    this.databaseId = params.databaseId || '(default)';
    if (!app) {
      try {
        app = getApp();
      } catch {
        const appOpts = {} as AppOptions;
        if (params.projectId) {
          appOpts.projectId = params.projectId;
        }
        app = initializeApp(appOpts);
      }
    }
    this.app = app;
    this.db = getFirestore(this.app, this.databaseId);
  }

  async save(traceId: string, traceData: TraceData): Promise<void> {
    console.debug(`saving ${Object.keys(traceData.spans).length} spans`);
    await this.db
      .collection(this.collection)
      .doc(traceId)
      .set(traceData, { merge: true });
  }

  async load(traceId: string): Promise<TraceData | undefined> {
    const data = (
      await this.db.collection(this.collection).doc(traceId).get()
    ).data();
    if (!data) {
      return undefined;
    }
    return TraceDataSchema.parse(data);
  }

  async list(query?: TraceQuery): Promise<TraceQueryResponse> {
    const data = await this.db
      .collection(this.collection)
      .orderBy('startTime', 'desc')
      .limit(query?.limit || 10)
      .get();
    // TODO: add continuation token support
    return { traces: data.docs.map((d) => d.data() as TraceData) };
  }
}

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

import { App, initializeApp, getApp, AppOptions } from 'firebase-admin/app';
import { getFirestore, Firestore } from 'firebase-admin/firestore';
import {
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateSchema,
  FlowStateStore,
} from '@genkit-ai/common';
import { logger } from '@genkit-ai/common/logging';

/**
 * Implementation of flow state store that persistes flow state in Firestore.
 */
export class FirestoreStateStore implements FlowStateStore {
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
    this.collection = params.collection || 'ai-flows';
    this.databaseId = params.databaseId || '(default)';
    // TODO: revisit the default app creation flow
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
    this.db.settings({ ignoreUndefinedProperties: true });
  }

  async load(id: string): Promise<FlowState | undefined> {
    const data = (
      await this.db.collection(this.collection).doc(id).get()
    ).data();
    if (!data) {
      return undefined;
    }
    return FlowStateSchema.parse(data);
  }

  async save(id: string, state: FlowState): Promise<void> {
    logger.debug(state, 'save state');
    await this.db.collection(this.collection).doc(id).set(state);
  }

  async list(query?: FlowStateQuery): Promise<FlowStateQueryResponse> {
    const data = await this.db
      .collection(this.collection)
      .orderBy('startTime', 'desc')
      .limit(query?.limit || 10)
      .get();
    // TODO: add continuation token support
    return { flowStates: data.docs.map((d) => d.data() as FlowState) };
  }
}

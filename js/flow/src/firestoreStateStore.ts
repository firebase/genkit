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
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateSchema,
  FlowStateStore,
} from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Firestore } from '@google-cloud/firestore';

/** Allow customers to set service account credentials via an environment variable. */
interface Credentials {
  client_email?: string;
  private_key?: string;
}

/**
 * Implementation of flow state store that persistes flow state in Firestore.
 */
export class FirestoreStateStore implements FlowStateStore {
  readonly db: Firestore;
  readonly collection: string;
  readonly databaseId: string;

  constructor(
    params: {
      collection?: string;
      databaseId?: string;
      projectId?: string;
      credentials?: Credentials;
    } = {}
  ) {
    this.collection = params.collection || 'genkit-flows';
    this.databaseId = params.databaseId || '(default)';
    this.db = new Firestore({
      databaseId: this.databaseId,
      ignoreUndefinedProperties: true,
      credentials: params.credentials,
    });
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
      flowStates: data.docs.map((d) => d.data() as FlowState),
      continuationToken:
        data.docs.length === limit
          ? `${lastVisible.data().startTime}`
          : undefined,
    };
  }
}

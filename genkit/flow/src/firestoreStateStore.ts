import { App, initializeApp, getApp, AppOptions } from 'firebase-admin/app';
import { getFirestore, Firestore } from 'firebase-admin/firestore';
import { FlowState, FlowStateQuery, FlowStateSchema, FlowStateStore, setGlobalFlowStateStore } from '@google-genkit/common';
import logging from '@google-genkit/common/logging';

/**
 * Configures default state store to use {@link FirestoreStateStore}.
 */
export function useFirestoreStateStore(
  params: {
    app?: App;
    collection?: string;
    databaseId?: string;
    projectId?: string;
  } = {}
) {
  setGlobalFlowStateStore(new FirestoreStateStore(params));
}

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
    logging.debug(state, 'save state');
    await this.db.collection(this.collection).doc(id).set(state);
  }

  async list(query?: FlowStateQuery): Promise<FlowState[]> {
    const data = await this.db.collection(this.collection).limit(query?.limit || 10).get();
    return data.docs.map(d => d.data() as FlowState);
  }
}

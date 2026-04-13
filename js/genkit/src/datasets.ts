/**
 * Copyright 2026 Google LLC
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

import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

/** The target surface a dataset is intended for. */
export type DatasetType =
  | 'UNKNOWN'
  | 'FLOW'
  | 'MODEL'
  | 'EXECUTABLE_PROMPT';

/** JSON schema hints for dataset `input` and `reference` fields. */
export interface DatasetSchema {
  inputSchema?: Record<string, unknown>;
  referenceSchema?: Record<string, unknown>;
}

/** User-facing sample shape accepted when creating or updating a dataset. */
export interface InferenceSample {
  testCaseId?: string;
  input: unknown;
  reference?: unknown;
}

/** Persisted dataset sample shape used by the developer UI. */
export interface DatasetSample {
  testCaseId: string;
  input: unknown;
  reference?: unknown;
}

/** Request payload for creating a dataset. */
export interface CreateDatasetRequest {
  data: InferenceSample[];
  datasetId?: string;
  datasetType: DatasetType;
  schema?: DatasetSchema;
  metricRefs?: string[];
  targetAction?: string;
}

/** Request payload for updating a dataset. */
export interface UpdateDatasetRequest {
  datasetId: string;
  data?: InferenceSample[];
  schema?: DatasetSchema;
  metricRefs?: string[];
  targetAction?: string;
}

/** Metadata shown for a dataset in the developer UI. */
export interface DatasetMetadata {
  datasetId: string;
  size: number;
  schema?: DatasetSchema;
  datasetType: DatasetType;
  targetAction?: string;
  metricRefs: string[];
  version: number;
  createTime: string;
  updateTime: string;
}

/**
 * DatasetStore is the narrow persistence boundary for eval datasets.
 *
 * The current developer UI expects the local `.genkit/datasets` file layout,
 * but callers should depend on this interface so a remote datastore can be
 * introduced later without changing the programmatic API.
 */
export interface DatasetStore {
  createDataset(req: CreateDatasetRequest): Promise<DatasetMetadata>;
  updateDataset(req: UpdateDatasetRequest): Promise<DatasetMetadata>;
  getDataset(datasetId: string): Promise<DatasetSample[]>;
  listDatasets(): Promise<DatasetMetadata[]>;
  deleteDataset(datasetId: string): Promise<void>;
}

const DATASET_ID_RE = /^[A-Za-z][A-Za-z0-9_.-]{4,34}[A-Za-z0-9]$/;

/**
 * LocalFileDatasetStore is the default DatasetStore implementation used by the
 * current developer UI. It persists `index.json` plus one `${datasetId}.json`
 * file under `.genkit/datasets`.
 */
export class LocalFileDatasetStore implements DatasetStore {
  readonly storeRoot: string;
  readonly indexFile: string;

  /** Creates a store rooted at a dataset directory. */
  constructor(storeRoot: string) {
    this.storeRoot = storeRoot;
    this.indexFile = path.join(storeRoot, 'index.json');
  }

  /** Returns the default local dataset store for a project root. */
  static async forProjectRoot(projectRoot = process.cwd()) {
    const store = new LocalFileDatasetStore(
      path.join(projectRoot, '.genkit', 'datasets')
    );
    await store.ensureInitialized();
    return store;
  }

  /** Creates a dataset using the current developer UI file format. */
  async createDataset(req: CreateDatasetRequest): Promise<DatasetMetadata> {
    await this.ensureInitialized();
    const metadataMap = await this.readMetadataMap();
    const datasetId = this.generateDatasetId(req.datasetId, metadataMap);
    const dataset = normalizeInferenceDataset(req.data);

    await writeFile(
      this.datasetFilePath(datasetId),
      JSON.stringify(dataset),
      'utf8'
    );

    const now = new Date().toString();
    const metadata: DatasetMetadata = {
      datasetId,
      size: dataset.length,
      schema: req.schema,
      datasetType: req.datasetType,
      targetAction: req.targetAction,
      metricRefs: [...(req.metricRefs ?? [])],
      version: 1,
      createTime: now,
      updateTime: now,
    };
    metadataMap[datasetId] = metadata;
    await this.writeMetadataMap(metadataMap);
    return metadata;
  }

  /** Updates a dataset and increments its version when sample data changes. */
  async updateDataset(req: UpdateDatasetRequest): Promise<DatasetMetadata> {
    await this.ensureInitialized();
    const filePath = this.datasetFilePath(req.datasetId);
    const metadataMap = await this.readMetadataMap();
    const prevMetadata = metadataMap[req.datasetId];
    if (!prevMetadata) {
      throw new Error('Update dataset failed: dataset metadata not found');
    }

    let newSize = prevMetadata.size;
    let version = prevMetadata.version;
    if (req.data) {
      const patched = await this.patchDataset(
        req.datasetId,
        normalizeInferenceDataset(req.data)
      );
      newSize = patched.length;
      version += 1;
    } else {
      await readFile(filePath, 'utf8');
    }

    const metadata: DatasetMetadata = {
      datasetId: req.datasetId,
      size: newSize,
      schema: req.schema ?? prevMetadata.schema,
      datasetType: prevMetadata.datasetType,
      targetAction: req.targetAction ?? prevMetadata.targetAction,
      metricRefs: req.metricRefs ? [...req.metricRefs] : [...prevMetadata.metricRefs],
      version,
      createTime: prevMetadata.createTime,
      updateTime: new Date().toString(),
    };
    metadataMap[req.datasetId] = metadata;
    await this.writeMetadataMap(metadataMap);
    return metadata;
  }

  /** Reads the persisted samples for a dataset ID. */
  async getDataset(datasetId: string): Promise<DatasetSample[]> {
    const raw = await readFile(this.datasetFilePath(datasetId), 'utf8');
    return JSON.parse(raw) as DatasetSample[];
  }

  /** Lists all dataset metadata records sorted by dataset ID. */
  async listDatasets(): Promise<DatasetMetadata[]> {
    const metadataMap = await this.readMetadataMap();
    return Object.keys(metadataMap)
      .sort()
      .map((datasetId) => metadataMap[datasetId]);
  }

  /** Deletes a dataset file and its metadata entry. */
  async deleteDataset(datasetId: string): Promise<void> {
    await rm(this.datasetFilePath(datasetId));
    const metadataMap = await this.readMetadataMap();
    delete metadataMap[datasetId];
    await this.writeMetadataMap(metadataMap);
  }

  private async ensureInitialized() {
    await mkdir(this.storeRoot, { recursive: true });
    try {
      await readFile(this.indexFile, 'utf8');
    } catch {
      await writeFile(this.indexFile, JSON.stringify({}), 'utf8');
    }
  }

  private async readMetadataMap(): Promise<Record<string, DatasetMetadata>> {
    const raw = await readFile(this.indexFile, 'utf8');
    return JSON.parse(raw) as Record<string, DatasetMetadata>;
  }

  private async writeMetadataMap(
    metadataMap: Record<string, DatasetMetadata>
  ): Promise<void> {
    await writeFile(this.indexFile, JSON.stringify(metadataMap), 'utf8');
  }

  private async patchDataset(
    datasetId: string,
    patch: DatasetSample[]
  ): Promise<DatasetSample[]> {
    const existing = await this.getDataset(datasetId);
    const datasetMap = new Map(existing.map((item) => [item.testCaseId, item]));
    for (const sample of patch) {
      datasetMap.set(sample.testCaseId, sample);
    }
    const merged = Array.from(datasetMap.values());
    await writeFile(
      this.datasetFilePath(datasetId),
      JSON.stringify(merged),
      'utf8'
    );
    return merged;
  }

  private generateDatasetId(
    datasetId: string | undefined,
    metadataMap: Record<string, DatasetMetadata>
  ) {
    if (!datasetId) {
      let generated = randomUUID();
      while (metadataMap[generated]) {
        generated = randomUUID();
      }
      return generated;
    }
    if (!DATASET_ID_RE.test(datasetId)) {
      throw new Error(
        'Invalid datasetId provided. ID must be alphanumeric, with hyphens, dots and dashes. Is must start with an alphabet, end with an alphabet or a number, and must be 6-36 characters long.'
      );
    }
    if (metadataMap[datasetId]) {
      throw new Error(`Dataset ID not unique: ${datasetId}`);
    }
    return datasetId;
  }

  private datasetFilePath(datasetId: string) {
    return path.join(this.storeRoot, `${datasetId}.json`);
  }
}

/**
 * Returns the default DatasetStore for the current project.
 *
 * Today this is file-backed so datasets render in the current developer UI.
 * Callers should keep using the DatasetStore interface so a remote
 * implementation can be swapped in later if needed.
 */
export async function datasetStoreForProjectRoot(
  projectRoot = process.cwd()
): Promise<DatasetStore> {
  return LocalFileDatasetStore.forProjectRoot(projectRoot);
}

function normalizeInferenceDataset(data: InferenceSample[]): DatasetSample[] {
  return data.map((sample) => ({
    testCaseId: sample.testCaseId ?? randomUUID(),
    input: sample.input,
    reference: sample.reference,
  }));
}

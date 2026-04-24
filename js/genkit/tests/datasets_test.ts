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

import * as assert from 'node:assert';
import { access, mkdtemp, readFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { describe, it } from 'node:test';
import { LocalFileDatasetStore } from '../src/index.js';

describe('LocalFileDatasetStore', () => {
  it('persists datasets in the developer UI format', async () => {
    const isolatedStore = new LocalFileDatasetStore(
      await mkdtemp(path.join(os.tmpdir(), 'genkit-datasets-'))
    );

    const created = await isolatedStore.createDataset({
      datasetId: 'dataset-1-123456',
      datasetType: 'FLOW',
      targetAction: '/flow/my-flow',
      data: [{ input: 'hello', reference: 'world' }],
    });

    assert.strictEqual(created.datasetId, 'dataset-1-123456');
    assert.strictEqual(created.version, 1);

    const listed = await isolatedStore.listDatasets();
    assert.strictEqual(listed.length, 1);

    const fetched = await isolatedStore.getDataset('dataset-1-123456');
    assert.strictEqual(fetched.length, 1);
    assert.ok(fetched[0].testCaseId);

    const updated = await isolatedStore.updateDataset({
      datasetId: 'dataset-1-123456',
      metricRefs: ['/evaluator/faithfulness'],
      data: [{ testCaseId: fetched[0].testCaseId, input: 'updated' }],
    });
    assert.strictEqual(updated.version, 2);
    assert.deepStrictEqual(updated.metricRefs, ['/evaluator/faithfulness']);

    const indexRaw = await readFile(
      path.join(isolatedStore.storeRoot, 'index.json'),
      'utf8'
    );
    const index = JSON.parse(indexRaw) as Record<string, { datasetId: string }>;
    assert.strictEqual(index['dataset-1-123456'].datasetId, 'dataset-1-123456');

    await isolatedStore.deleteDataset('dataset-1-123456');
    await assert.rejects(
      access(path.join(isolatedStore.storeRoot, 'dataset-1-123456.json'))
    );
  });
});

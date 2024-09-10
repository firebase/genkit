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
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  jest,
} from '@jest/globals';
import fs from 'fs';
import { LocalFileDatasetStore } from '../../src/eval/localFileDatasetStore';
import {
  CreateDatasetRequestSchema,
  UpdateDatasetRequestSchema,
} from '../../src/types/apis';
import { DatasetStore } from '../../src/types/eval';

const FAKE_TIME = new Date('2024-02-03T12:05:33.243Z');

const SAMPLE_DATASET_1_V1 = {
  samples: [
    {
      input: 'Cats are evil',
      reference: 'Sorry no reference',
    },
    {
      input: 'Dogs are beautiful',
    },
  ],
};

const SAMPLE_DATASET_1_V2 = {
  samples: [
    {
      input: 'Cats are evil',
      reference: 'Sorry no reference',
    },
    {
      input: 'Dogs are angels',
    },
    {
      input: 'Dogs are also super cute',
    },
  ],
};

const SAMPLE_DATASET_ID_1 = '12345678';
const SAMPLE_DATASET_NAME_1 = 'dataset-1';

const SAMPLE_DATASET_METADATA_1_V1 = {
  datasetId: SAMPLE_DATASET_ID_1,
  size: 2,
  version: 1,
  displayName: SAMPLE_DATASET_NAME_1,
  createTime: FAKE_TIME.toString(),
  updateTime: FAKE_TIME.toString(),
};
const SAMPLE_DATASET_METADATA_1_V2 = {
  datasetId: SAMPLE_DATASET_ID_1,
  size: 3,
  version: 2,
  displayName: SAMPLE_DATASET_NAME_1,
  createTime: FAKE_TIME.toString(),
  updateTime: FAKE_TIME.toString(),
};

const CREATE_DATASET_REQUEST = CreateDatasetRequestSchema.parse({
  data: SAMPLE_DATASET_1_V1,
  displayName: SAMPLE_DATASET_NAME_1,
});

const UPDATE_DATASET_REQUEST = UpdateDatasetRequestSchema.parse({
  data: SAMPLE_DATASET_1_V2,
  datasetId: SAMPLE_DATASET_ID_1,
  displayName: SAMPLE_DATASET_NAME_1,
});

const SAMPLE_DATASET_ID_2 = '22345678';
const SAMPLE_DATASET_NAME_2 = 'dataset-2';

const SAMPLE_DATASET_METADATA_2 = {
  datasetId: SAMPLE_DATASET_ID_2,
  size: 5,
  version: 1,
  displayName: SAMPLE_DATASET_NAME_2,
  createTime: FAKE_TIME.toString(),
  updateTime: FAKE_TIME.toString(),
};

jest.mock('crypto', () => {
  return {
    createHash: jest.fn().mockReturnThis(),
    update: jest.fn().mockReturnThis(),
    digest: jest.fn(() => 'store-root'),
  };
});

jest.mock('uuid', () => ({
  v4: () => SAMPLE_DATASET_ID_1,
}));

jest.useFakeTimers({ advanceTimers: true });
jest.setSystemTime(FAKE_TIME);

describe('localFileDatasetStore', () => {
  let DatasetStore: DatasetStore;

  beforeEach(() => {
    // For storeRoot setup
    fs.existsSync = jest.fn(() => true);
    LocalFileDatasetStore.reset();
    DatasetStore = LocalFileDatasetStore.getDatasetStore() as DatasetStore;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('createDataset', () => {
    it('writes and updates index for new dataset', async () => {
      fs.promises.writeFile = jest.fn(async () => Promise.resolve(undefined));
      fs.promises.appendFile = jest.fn(async () => Promise.resolve(undefined));
      // For index file reads
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve(JSON.stringify({}) as any)
      );
      fs.existsSync = jest.fn(() => false);

      const datasetMetadata = await DatasetStore.createDataset(
        CREATE_DATASET_REQUEST
      );

      expect(fs.promises.writeFile).toHaveBeenCalledTimes(2);
      expect(fs.promises.writeFile).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('datasets/12345678.json'),
        JSON.stringify(CREATE_DATASET_REQUEST.data)
      );
      const metadataMap = {
        [SAMPLE_DATASET_ID_1]: SAMPLE_DATASET_METADATA_1_V1,
      };
      expect(fs.promises.writeFile).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('datasets/index.json'),
        JSON.stringify(metadataMap)
      );
      expect(datasetMetadata).toMatchObject(SAMPLE_DATASET_METADATA_1_V1);
    });

    it('fails request if dataset already exists', async () => {
      fs.existsSync = jest.fn(() => true);

      expect(async () => {
        await DatasetStore.createDataset(CREATE_DATASET_REQUEST);
      }).rejects.toThrow();

      expect(fs.promises.writeFile).toBeCalledTimes(0);
    });
  });

  describe('updateDataset', () => {
    it('succeeds for existing dataset', async () => {
      fs.existsSync = jest.fn(() => true);
      let metadataMap = {
        [SAMPLE_DATASET_ID_1]: SAMPLE_DATASET_METADATA_1_V1,
        [SAMPLE_DATASET_ID_2]: SAMPLE_DATASET_METADATA_2,
      };
      // For index file reads
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve(JSON.stringify(metadataMap) as any)
      );
      fs.promises.writeFile = jest.fn(async () => Promise.resolve(undefined));
      fs.promises.appendFile = jest.fn(async () => Promise.resolve(undefined));

      const datasetMetadata = await DatasetStore.updateDataset(
        UPDATE_DATASET_REQUEST
      );

      expect(fs.promises.writeFile).toHaveBeenCalledTimes(2);
      expect(fs.promises.writeFile).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('datasets/12345678.json'),
        JSON.stringify(SAMPLE_DATASET_1_V2)
      );
      const updatedMetadataMap = {
        [SAMPLE_DATASET_ID_1]: SAMPLE_DATASET_METADATA_1_V2,
        [SAMPLE_DATASET_ID_2]: SAMPLE_DATASET_METADATA_2,
      };
      expect(fs.promises.writeFile).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('datasets/index.json'),
        JSON.stringify(updatedMetadataMap)
      );
      expect(datasetMetadata).toMatchObject(SAMPLE_DATASET_METADATA_1_V2);
    });

    it('fails if data is not passed', async () => {
      fs.existsSync = jest.fn(() => true);

      expect(async () => {
        await DatasetStore.updateDataset({
          datasetId: SAMPLE_DATASET_ID_1,
          displayName: SAMPLE_DATASET_NAME_1,
        });
      }).rejects.toThrow(
        new Error('Error: `data` is required for updateDataset')
      );

      expect(fs.promises.writeFile).toBeCalledTimes(0);
    });

    it('fails for non existing dataset', async () => {
      fs.existsSync = jest.fn(() => false);

      expect(async () => {
        await DatasetStore.updateDataset(UPDATE_DATASET_REQUEST);
      }).rejects.toThrow();

      expect(fs.promises.writeFile).toBeCalledTimes(0);
    });
  });

  describe('listDatasets', () => {
    it('succeeds for zero datasets', async () => {
      fs.existsSync = jest.fn(() => false);

      const metadatas = await DatasetStore.listDatasets();

      expect(metadatas).toMatchObject([]);
    });

    it('succeeds for existing datasets', async () => {
      fs.existsSync = jest.fn(() => true);
      const metadataMap = {
        [SAMPLE_DATASET_ID_1]: SAMPLE_DATASET_METADATA_1_V1,
        [SAMPLE_DATASET_ID_2]: SAMPLE_DATASET_METADATA_2,
      };
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve(JSON.stringify(metadataMap) as any)
      );

      const metadatas = await DatasetStore.listDatasets();

      expect(metadatas).toMatchObject([
        SAMPLE_DATASET_METADATA_1_V1,
        SAMPLE_DATASET_METADATA_2,
      ]);
    });
  });

  describe('getDataset', () => {
    it('succeeds for existing dataset', async () => {
      fs.existsSync = jest.fn(() => true);
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve(JSON.stringify(SAMPLE_DATASET_1_V1) as any)
      );

      const fetchedDataset = await DatasetStore.getDataset(SAMPLE_DATASET_ID_1);

      expect(fetchedDataset).toMatchObject(SAMPLE_DATASET_1_V1);
    });

    it('fails for non existing dataset', async () => {
      // TODO: Implement this.
    });
  });

  describe('deleteDataset', () => {
    it('deletes dataset and updates index', async () => {
      fs.promises.rm = jest.fn(async () => Promise.resolve());
      let metadataMap = {
        [SAMPLE_DATASET_ID_1]: SAMPLE_DATASET_METADATA_1_V1,
        [SAMPLE_DATASET_ID_2]: SAMPLE_DATASET_METADATA_2,
      };
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve(JSON.stringify(metadataMap) as any)
      );

      await DatasetStore.deleteDataset(SAMPLE_DATASET_ID_1);

      expect(fs.promises.rm).toHaveBeenCalledWith(
        expect.stringContaining('datasets/12345678.json')
      );
      let updatedMetadataMap = {
        [SAMPLE_DATASET_ID_2]: SAMPLE_DATASET_METADATA_2,
      };
      expect(fs.promises.writeFile).toHaveBeenCalledWith(
        expect.stringContaining('datasets/index.json'),
        JSON.stringify(updatedMetadataMap)
      );
    });
  });
});

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
import { LocalFileEvalStore } from '../../src/eval/localFileEvalStore';
import { EvalResult, EvalRunSchema, EvalStore } from '../../src/types/eval';

const EVAL_RESULTS: EvalResult[] = [
  {
    testCaseId: 'alakjdshfalsdkjh',
    input: { subject: 'Kermit the Frog', style: 'Jerry Seinfeld' },
    output: `So, here's the thing about Kermit the Frog, right? He's got this whole \"it's not easy being green\"
        routine.  Which, I mean, relatable, right? We've all got our things...But, the guy's a frog! He
        lives in a swamp! You chose this, Kermit! You could be any color...you picked the one that blends
        in perfectly with your natural habitat.`,
    context: [
      'Kermit has a song called "It\'s not easy being green"',
      'Kermit is in a complicated relationship with Miss Piggy',
    ],
    metrics: [
      {
        evaluator: 'faithfulness',
        score: 0.5,
        rationale: 'One out of two claims can be inferred from the context',
      },
    ],
    traceIds: [],
  },
  {
    testCaseId: 'lkjhasdfkljahsdf',
    input: { subject: "Doctor's office", style: 'Wanda Sykes' },
    output: `Okay, check this out. You ever been to one of those doctor's offices where it takes you a year to get an appointment, 
      then they stick you in a waiting room with magazines from like, 1997? It's like, are they expecting me to catch up on all the
      Kardashian drama from the Bush administration?`,
    context: [],
    metrics: [
      {
        evaluator: 'faithfulness',
        score: 0,
        rationale: 'No context was provided',
      },
    ],
    traceIds: [],
  },
];

const METRICS_METADATA = {
  faithfulness: {
    displayName: 'Faithfullness',
    definition: 'Faitfulness definition',
  },
};

const EVAL_RUN_WITH_ACTION = EvalRunSchema.parse({
  key: {
    actionRef: 'flow/tellMeAJoke',
    evalRunId: 'abc1234',
    createdAt: new Date().toISOString(),
  },
  results: EVAL_RESULTS,
  metricMetadata: METRICS_METADATA,
});

const EVAL_RUN_WITHOUT_ACTION = EvalRunSchema.parse({
  key: {
    evalRunId: 'def456',
    createdAt: new Date().toISOString(),
  },
  results: EVAL_RESULTS,
  metricMetadata: METRICS_METADATA,
});

describe('localFileEvalStore', () => {
  let evalStore: EvalStore;

  beforeEach(() => {
    // For storeRoot setup
    fs.existsSync = jest.fn(() => true);
    LocalFileEvalStore.reset();
    evalStore = LocalFileEvalStore.getEvalStore() as EvalStore;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('save', () => {
    beforeEach(() => {
      fs.promises.writeFile = jest.fn(async () => Promise.resolve(undefined));
      fs.promises.appendFile = jest.fn(async () => Promise.resolve(undefined));
    });

    it('writes and updates index for eval run with actionId', async () => {
      await evalStore.save(EVAL_RUN_WITH_ACTION);

      expect(fs.promises.writeFile).toHaveBeenCalledWith(
        expect.stringContaining(`evals/abc1234.json`),
        JSON.stringify(EVAL_RUN_WITH_ACTION)
      );
      expect(fs.promises.appendFile).toHaveBeenCalledWith(
        expect.stringContaining(`evals/index.txt`),
        JSON.stringify(EVAL_RUN_WITH_ACTION.key) + '\n'
      );
    });

    it('persists a new evalRun file without an actionId', async () => {
      await evalStore.save(EVAL_RUN_WITHOUT_ACTION);

      expect(fs.promises.writeFile).toHaveBeenCalledWith(
        expect.stringContaining(`evals/def456.json`),
        JSON.stringify(EVAL_RUN_WITHOUT_ACTION)
      );
      expect(fs.promises.appendFile).toHaveBeenCalledWith(
        expect.stringContaining(`evals/index.txt`),
        JSON.stringify(EVAL_RUN_WITHOUT_ACTION.key) + '\n'
      );
    });
  });

  describe('load', () => {
    it('fetches an evalRun file by id with actionId', async () => {
      fs.existsSync = jest.fn(() => true);
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve(JSON.stringify(EVAL_RUN_WITH_ACTION) as any)
      );
      const fetchedEvalRun = await evalStore.load(
        EVAL_RUN_WITH_ACTION.key.evalRunId
      );
      expect(fetchedEvalRun).toMatchObject(EVAL_RUN_WITH_ACTION);
    });

    it('fetches an evalRun file by id with no actionId', async () => {
      fs.existsSync = jest.fn(() => true);
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve(JSON.stringify(EVAL_RUN_WITHOUT_ACTION) as any)
      );
      const fetchedEvalRun = await evalStore.load(
        EVAL_RUN_WITHOUT_ACTION.key.evalRunId
      );
      expect(fetchedEvalRun).toMatchObject(EVAL_RUN_WITHOUT_ACTION);
    });

    it('returns undefined if file does not exist', async () => {
      fs.existsSync = jest.fn(() => false);

      const fetchedEvalRun = await evalStore.load(
        EVAL_RUN_WITH_ACTION.key.evalRunId
      );
      expect(fetchedEvalRun).toBeUndefined();
    });
  });

  describe('list', () => {
    const EVAL_KEY_WITH_ACTION =
      JSON.stringify(EVAL_RUN_WITH_ACTION.key) + '\n';
    const EVAL_KEY_WITHOUT_ACTION =
      JSON.stringify(EVAL_RUN_WITHOUT_ACTION.key) + '\n';

    it('lists all evalRun keys from file', async () => {
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve((EVAL_KEY_WITH_ACTION + EVAL_KEY_WITHOUT_ACTION) as any)
      );
      const fetchedEvalKeys = await evalStore.list();

      const expectedKeys = {
        evalRunKeys: [EVAL_RUN_WITH_ACTION.key, EVAL_RUN_WITHOUT_ACTION.key],
      };
      expect(fetchedEvalKeys).toMatchObject(expectedKeys);
    });

    it('lists all evalRun keys for a flow', async () => {
      fs.promises.readFile = jest.fn(async () =>
        Promise.resolve((EVAL_KEY_WITH_ACTION + EVAL_KEY_WITHOUT_ACTION) as any)
      );

      const fetchedEvalKeys = await evalStore.list({
        filter: { actionRef: EVAL_RUN_WITH_ACTION.key.actionRef },
      });

      const expectedKeys = { evalRunKeys: [EVAL_RUN_WITH_ACTION.key] };
      expect(fetchedEvalKeys).toMatchObject(expectedKeys);
    });

    it('lists all evalRun keys from empty file', async () => {
      fs.promises.readFile = jest.fn(async () => Promise.resolve('' as any));
      const fetchedEvalKeys = await evalStore.list();

      const expectedKeys = {
        evalRunKeys: [],
      };
      expect(fetchedEvalKeys).toMatchObject(expectedKeys);
    });
  });
});

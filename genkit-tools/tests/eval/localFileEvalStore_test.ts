//import { describe, it, afterEach, beforeEach } from 'node:test';
import { describe, it, beforeEach, expect } from '@jest/globals';
import path from 'path';
import { vol } from 'memfs';
import fs from 'fs';
import {
  EvalRunSchema,
  LocalFileEvalStore,
  EvalRun,
  EvalResult,
} from '../../src/eval';

jest.mock('fs');
jest.mock('fs/promises');

describe('localFileEvalStore', () => {
  var evalStore: LocalFileEvalStore;
  var storeRoot: string;
  const evalRunResults: EvalResult[] = [
    {
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
          evaluator: 'context_precision',
          score: 0.5,
          rationale:
            'One out of two pieces of context were used in the output.',
        },
      ],
      traceIds: [],
    },
    {
      input: { subject: "Doctor's office", style: 'Wanda Sykes' },
      output: `Okay, check this out. You ever been to one of those doctor's offices where it takes you a year to get an appointment, 
        then they stick you in a waiting room with magazines from like, 1997? It's like, are they expecting me to catch up on all the
        Kardashian drama from the Bush administration?`,
      context: [],
      metrics: [
        {
          evaluator: 'context_precision',
          score: 0,
          rationale: 'No context was provided',
        },
      ],
      traceIds: [],
    },
  ];

  const evalRunWithAction = EvalRunSchema.parse({
    key: {
      actionId: 'flow/tellMeAJoke',
      evalRunId: 'abc1234',
      createdAt: new Date(),
    },
    results: evalRunResults,
  });

  const evalRunWithoutAction = EvalRunSchema.parse({
    key: {
      evalRunId: 'def456',
      createdAt: new Date(),
    },
    results: evalRunResults,
  });

  const writeManual = (evalRun: EvalRun) => {
    const fileName = evalStore.generateFileName(
      evalRun.key.evalRunId,
      evalRun.key.actionId
    );
    fs.writeFileSync(
      path.resolve(storeRoot, fileName),
      JSON.stringify(evalRun)
    );
  };

  const writeIndexManual = (evalRun: EvalRun) => {
    const indexFile = evalStore.getIndexFilePath();
    fs.appendFileSync(indexFile, JSON.stringify(evalRun.key) + '\n');
  };

  beforeEach(() => {
    vol.reset();
    evalStore = new LocalFileEvalStore();
    storeRoot = evalStore.generateRootPath();
  });

  describe('save', () => {
    it('persists a new evalRun file with an actionId', async () => {
      await evalStore.save(evalRunWithAction);
      const filePath = path.resolve(
        storeRoot,
        evalStore.generateFileName(
          evalRunWithAction.key.evalRunId,
          evalRunWithAction.key.actionId
        )
      );
      expect(fs.existsSync(filePath)).toBeTruthy();
    });

    it('persists a new evalRun file without an actionId', async () => {
      await evalStore.save(evalRunWithoutAction);
      const filePath = path.resolve(
        storeRoot,
        evalStore.generateFileName(evalRunWithoutAction.key.evalRunId)
      );
      expect(fs.existsSync(filePath)).toBeTruthy();
    });
  });

  describe('load', () => {
    it('fetches an evalRun file by id with actionId', async () => {
      writeManual(evalRunWithAction);
      const fetchedEvalRun = await evalStore.load(
        evalRunWithAction.key.evalRunId,
        evalRunWithAction.key.actionId
      );
      expect(fetchedEvalRun).toMatchObject(evalRunWithAction);
    });

    it('fetches an evalRun file by id with no actionId', async () => {
      writeManual(evalRunWithoutAction);
      const fetchedEvalRun = await evalStore.load(
        evalRunWithoutAction.key.evalRunId
      );
      expect(fetchedEvalRun).toMatchObject(evalRunWithoutAction);
    });
  });

  describe('list', () => {
    it('lists all evalRun keys from file', async () => {
      writeIndexManual(evalRunWithAction);
      writeIndexManual(evalRunWithoutAction);

      const fetchedEvalKeys = await evalStore.list();

      const expectedKeys = {
        results: [evalRunWithAction.key, evalRunWithoutAction.key],
      };
      expect(fetchedEvalKeys).toMatchObject(expectedKeys);
    });

    it('lists all evalRun keys for a flow', async () => {
      await evalStore.save(evalRunWithAction);
      await evalStore.save(evalRunWithoutAction);

      const fetchedEvalKeys = await evalStore.list({
        filter: { actionId: evalRunWithAction.key.actionId },
      });

      const expectedKeys = { results: [evalRunWithAction.key] };
      expect(fetchedEvalKeys).toMatchObject(expectedKeys);
    });
  });
});

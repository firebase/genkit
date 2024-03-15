import { logger } from '../utils/logger';
import os from 'os';
import fs from 'fs';
import { readFile, writeFile, appendFile } from 'fs/promises';
import path from 'path';
import crypto from 'crypto';

import {
  ListEvalKeysRequest,
  ListEvalKeysResponse,
  EvalRunKeySchema,
  EvalRunKey,
  EvalRun,
  EvalRunSchema,
  EvalStore,
} from './types';

export class LocalFileEvalStore implements EvalStore {
  private readonly storeRoot;
  private readonly indexFile;
  private readonly indexDelimiter = '\n';

  constructor() {
    this.storeRoot = this.generateRootPath();
    this.indexFile = this.getIndexFilePath();
    fs.mkdirSync(this.storeRoot, { recursive: true });
    if (!fs.existsSync(this.indexFile)) {
      fs.writeFileSync(path.resolve(this.indexFile), '');
    }
    logger.info(`Initialized local file eval store at root: ${this.storeRoot}`);
  }

  async save(evalRun: EvalRun): Promise<void> {
    const fileName = this.generateFileName(
      evalRun.key.evalRunId,
      evalRun.key.actionId
    );

    logger.info(
      `Saving EvalRun ${evalRun.key.evalRunId} to ` +
        path.resolve(this.storeRoot, fileName)
    );
    await writeFile(
      path.resolve(this.storeRoot, fileName),
      JSON.stringify(evalRun)
    );

    logger.debug(
      `Save EvalRunKey ${JSON.stringify(evalRun.key)} to ` +
        path.resolve(this.indexFile)
    );
    await appendFile(
      path.resolve(this.indexFile),
      JSON.stringify(evalRun.key) + this.indexDelimiter
    );
  }

  async load(
    evalRunId: string,
    actionId?: string
  ): Promise<EvalRun | undefined> {
    const filePath = path.resolve(
      this.storeRoot,
      this.generateFileName(evalRunId, actionId)
    );
    if (!fs.existsSync(filePath)) {
      return undefined;
    }
    return await readFile(filePath, 'utf8').then((data) =>
      EvalRunSchema.parse(JSON.parse(data))
    );
  }

  async list(
    query?: ListEvalKeysRequest | undefined
  ): Promise<ListEvalKeysResponse> {
    var keys = await readFile(this.indexFile, 'utf8').then((data) =>
      // strip the final carriage return before parsing all lines
      data.slice(0, -1).split(this.indexDelimiter).map(this.parseLineToKey)
    );

    logger.debug(`Found keys: ${JSON.stringify(keys)}`);

    if (query?.filter?.actionId) {
      keys = keys.filter((key) => key.actionId === query?.filter?.actionId);
      logger.debug(`Filtered keys: ${JSON.stringify(keys)}`);
    }

    return {
      results: keys,
    };
  }

  generateFileName(evalRunId: string, actionId?: string): string {
    if (!actionId) {
      return `${evalRunId}.json`;
    }

    return `${actionId?.replace('/', '_')}-${evalRunId}.json`;
  }

  getIndexFilePath(): string {
    return path.resolve(this.storeRoot, 'index.txt');
  }

  parseLineToKey(key: string): EvalRunKey {
    return EvalRunKeySchema.parse(JSON.parse(key));
  }

  generateRootPath(): string {
    const rootHash = crypto
      .createHash('md5')
      .update(require?.main?.filename || 'unknown')
      .digest('hex');
    return path.resolve(os.tmpdir(), `.genkit/${rootHash}/evals`);
  }
}

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

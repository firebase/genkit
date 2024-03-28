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

import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import {
  FlowState,
  FlowStateQuery,
  FlowStateQueryResponse,
  FlowStateSchema,
  FlowStateStore,
} from './flowTypes.js';
import { logger } from './logging.js';

/**
 * Implementation of flow state store that persistes flow state on local disk.
 */
export class LocalFileFlowStateStore implements FlowStateStore {
  private readonly storeRoot: string;

  constructor() {
    const rootHash = crypto
      .createHash('md5')
      .update(require?.main?.filename || 'unknown')
      .digest('hex');
    this.storeRoot = path.resolve(os.tmpdir(), `.genkit/${rootHash}/flows`);
    fs.mkdirSync(this.storeRoot, { recursive: true });
    logger.info('Using DevFlowStateStore. Root: ' + this.storeRoot);
  }

  async load(id: string): Promise<FlowState | undefined> {
    const filePath = path.resolve(this.storeRoot, `${id}`);
    if (!fs.existsSync(filePath)) {
      return undefined;
    }
    const data = fs.readFileSync(filePath, 'utf8');
    return FlowStateSchema.parse(JSON.parse(data));
  }

  async save(id: string, state: FlowState): Promise<void> {
    logger.debug('save flow state ' + id);
    fs.writeFileSync(
      path.resolve(this.storeRoot, `${id}`),
      JSON.stringify(state)
    );
  }

  async list(query?: FlowStateQuery): Promise<FlowStateQueryResponse> {
    const files = fs.readdirSync(this.storeRoot);
    files.sort((a, b) => {
      return (
        fs.statSync(path.resolve(this.storeRoot, `${b}`)).mtime.getTime() -
        fs.statSync(path.resolve(this.storeRoot, `${a}`)).mtime.getTime()
      );
    });
    const startFrom = query?.continuationToken
      ? parseInt(query?.continuationToken)
      : 0;
    const stopAt = startFrom + (query?.limit || 10);
    const flowStates = files.slice(startFrom, stopAt).map((id) => {
      const filePath = path.resolve(this.storeRoot, `${id}`);
      const data = fs.readFileSync(filePath, 'utf8');
      return FlowStateSchema.parse(JSON.parse(data));
    });
    return {
      flowStates,
      continuationToken: files.length > stopAt ? stopAt.toString() : undefined,
    };
  }
}

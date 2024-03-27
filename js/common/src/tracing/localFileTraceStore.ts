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
import { logger } from '../logging';
import {
  TraceData,
  TraceDataSchema,
  TraceQuery,
  TraceQueryResponse,
  TraceStore,
} from './types.js';

/**
 * Implementation of trace store that persists traces on local disk.
 */
export class LocalFileTraceStore implements TraceStore {
  private readonly storeRoot;

  constructor() {
    const rootHash = crypto
      .createHash('md5')
      .update(require?.main?.filename || 'unknown')
      .digest('hex');
    this.storeRoot = path.resolve(os.tmpdir(), `.genkit/${rootHash}/traces`);
    fs.mkdirSync(this.storeRoot, { recursive: true });
    logger.info(
      `Initialized local file trace store at root: ${this.storeRoot}`
    );
  }

  async load(id: string): Promise<TraceData | undefined> {
    const filePath = path.resolve(this.storeRoot, `${id}`);
    if (!fs.existsSync(filePath)) {
      return undefined;
    }
    const data = fs.readFileSync(filePath, 'utf8');
    const parsed = JSON.parse(data);
    // For backwards compatibility, new field.
    if (!parsed.traceId) {
      parsed.traceId = id;
    }
    return TraceDataSchema.parse(parsed);
  }

  async save(id: string, trace: TraceData): Promise<void> {
    const existsing = await this.load(id);
    if (existsing) {
      Object.keys(trace.spans).forEach(
        (spanId) => (existsing.spans[spanId] = trace.spans[spanId])
      );
      existsing.displayName = trace.displayName;
      existsing.startTime = trace.startTime;
      existsing.endTime = trace.endTime;
      trace = existsing;
    }
    logger.debug(
      `save trace ${id} to ` + path.resolve(this.storeRoot, `${id}`)
    );
    fs.writeFileSync(
      path.resolve(this.storeRoot, `${id}`),
      JSON.stringify(trace)
    );
  }

  async list(query?: TraceQuery): Promise<TraceQueryResponse> {
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
    const traces = files.slice(startFrom, stopAt).map((id) => {
      const filePath = path.resolve(this.storeRoot, `${id}`);
      const data = fs.readFileSync(filePath, 'utf8');
      const parsed = JSON.parse(data);
      // For backwards compatibility, new field.
      if (!parsed.traceId) {
        parsed.traceId = id;
      }
      return TraceDataSchema.parse(parsed);
    });
    return {
      traces,
      continuationToken:
        files.length > stopAt ? (stopAt + 1).toString() : undefined,
    };
  }
}

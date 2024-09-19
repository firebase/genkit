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

import { TraceData, TraceDataSchema } from '@genkit-ai/tools-common';
import { Mutex } from 'async-mutex';
import fs from 'fs';
import path from 'path';
import { TraceQuery, TraceQueryResponse, TraceStore } from './types';

/**
 * Implementation of trace store that persists traces on local disk.
 */
export class LocalFileTraceStore implements TraceStore {
  private readonly storeRoot;
  private mutexes: Record<string, Mutex> = {};
  private filters: Record<string, string>;

  static defaultFilters: Record<string, string> = {
    // Prevent prompt rendering from spamming local trace store
    'genkit:metadata:subtype': 'prompt',
  };

  constructor(filters = LocalFileTraceStore.defaultFilters) {
    this.storeRoot = path.resolve(process.cwd(), `.genkit/traces`);
    fs.mkdirSync(this.storeRoot, { recursive: true });
    console.info(
      `[Telemetry Server] initialized local file trace store at root: ${this.storeRoot}`
    );
    this.filters = filters;
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

  getMutex(id: string): Mutex {
    if (!this.mutexes[id]) {
      this.mutexes[id] = new Mutex();
    }
    return this.mutexes[id];
  }

  async save(id: string, rawTrace: TraceData): Promise<void> {
    let trace = this.filter(rawTrace);
    if (Object.keys(trace.spans).length === 0) {
      return;
    }
    const mutex = this.getMutex(id);
    await mutex.waitForUnlock();
    const release = await mutex.acquire();
    try {
      const existing = await this.load(id);
      if (existing) {
        Object.keys(trace.spans).forEach(
          (spanId) => (existing.spans[spanId] = trace.spans[spanId])
        );
        existing.displayName = trace.displayName;
        existing.startTime = trace.startTime;
        existing.endTime = trace.endTime;
        trace = existing;
      }
      fs.writeFileSync(
        path.resolve(this.storeRoot, `${id}`),
        JSON.stringify(trace)
      );
    } finally {
      release();
    }
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
      continuationToken: files.length > stopAt ? stopAt.toString() : undefined,
    };
  }

  private filter(trace: TraceData): TraceData {
    // Delete any spans that match the filter criteria
    Object.keys(trace.spans).forEach((spanId) => {
      const span = trace.spans[spanId];
      Object.keys(this.filters).forEach((f) => {
        if (span.attributes[f] === this.filters[f]) {
          delete trace.spans[spanId];
        }
      });
    });
    // Delete the root wrapper if it's the only span left
    if (Object.keys(trace.spans).length === 1) {
      Object.keys(trace.spans).forEach((spanId) => {
        const span = trace.spans[spanId];
        if (span.attributes['genkit:name'] === 'dev-run-action-wrapper') {
          delete trace.spans[spanId];
        }
      });
    }
    return trace;
  }
}

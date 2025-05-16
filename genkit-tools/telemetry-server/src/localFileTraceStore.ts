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
  TraceDataSchema,
  TraceQueryFilter,
  type TraceData,
} from '@genkit-ai/tools-common';
import { Mutex } from 'async-mutex';
import fs from 'fs';
import lockfile from 'lockfile';
import os from 'os';
import path from 'path';
import { TraceQuery, TraceQueryResponse, TraceStore } from './types';

const MAX_TRACES = 1000;

/**
 * Implementation of trace store that persists traces on local disk.
 */
export class LocalFileTraceStore implements TraceStore {
  private readonly storeRoot;
  private readonly indexRoot;
  private mutexes: Record<string, Mutex> = {};
  private filters: Record<string, string>;
  private readonly index: Index | undefined;

  static defaultFilters: Record<string, string> = {
    // Prevent prompt rendering from spamming local trace store
    'genkit:metadata:subtype': 'prompt',
  };

  constructor(options?: {
    filters?: Record<string, string>;
    storeRoot?: string;
    indexRoot?: string;
    useIndex?: boolean;
  }) {
    this.storeRoot =
      options?.storeRoot ?? path.resolve(process.cwd(), `.genkit/traces`);
    // Index is ephemeral, gets rebuilt on every restart. It's done for simplicity
    // for now, so that we can tweak index format without having to worry about
    // backwards compatibility. In the future we can keep indexes around between
    // restarts and only rebuild if we detect corruption.
    this.indexRoot = path.resolve(
      os.tmpdir(),
      `./genkit-trace-index-${Date.now()}-${Math.random()}`
    );
    fs.mkdirSync(this.storeRoot, { recursive: true });
    console.info(
      `[Telemetry Server] initialized local file trace store at root: ${this.storeRoot}`
    );
    this.filters = options?.filters ?? LocalFileTraceStore.defaultFilters;
    if (options?.useIndex) {
      this.index = new Index(this.indexRoot);
    }
  }

  async init() {
    if (!this.index) {
      return;
    }
    const time = Date.now();
    // Index only the last MAX_TRACES traces.
    const list = await this.listFromFiles({ limit: MAX_TRACES });
    for (const trace of list.traces.reverse()) {
      const hasRootSpan = !!Object.values(trace.spans).find(
        (s) => !s.parentSpanId
      );
      if (!hasRootSpan) continue;
      this.index.add(trace);
    }
    console.log(
      `Indexed ${list.traces.length} traces in ${Date.now() - time}ms in ${this.indexRoot}`
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
      const hasRootSpan = !!Object.values(rawTrace.spans).find(
        (s) => !s.parentSpanId
      );
      if (this.index && hasRootSpan) {
        // re-load the full trace, there are likely spans written there previously.
        const fullTrace = await this.load(rawTrace.traceId);
        if (!fullTrace) {
          throw new Error(
            'unable to read the trace that was just written... "this should never happen"'
          );
        }
        this.index.add(fullTrace);
      }
    } finally {
      release();
    }
  }

  async list(query?: TraceQuery): Promise<TraceQueryResponse> {
    if (!this.index) {
      return this.listFromFiles(query);
    }

    const searchResult = this.index.search({
      limit: query?.limit ?? 10,
      startFromIndex: query?.continuationToken
        ? parseInt(query?.continuationToken)
        : undefined,
      filter: query?.filter,
    });

    const loadedTraces = await Promise.all(
      searchResult.data.map((d) => this.load(d['id']))
    );

    return {
      traces: loadedTraces.filter((t) => !!t) as TraceData[],
      continuationToken: searchResult.pageLastIndex
        ? `${searchResult.pageLastIndex}`
        : undefined,
    };
  }

  private async listFromFiles(query?: TraceQuery): Promise<TraceQueryResponse> {
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

export interface IndexSearchResult {
  pageLastIndex?: number;
  data: Record<string, string>[];
}

/**
 * A super basic searchable index implementation. It's not particularly efficient,
 * but should not be worse than reading individual trace files from disk.
 */
export class Index {
  private currentIndexFile: string;

  constructor(private indexRoot: string) {
    // TODO: do something about index getting too big. Delete/forget old stuff, etc.
    this.currentIndexFile = path.resolve(this.indexRoot, '1.idx');
    fs.mkdirSync(this.indexRoot, { recursive: true });
    if (!fs.existsSync(this.currentIndexFile)) {
      fs.writeFileSync(this.currentIndexFile, '');
    }
  }

  add(traceData: TraceData) {
    const rootSpans = Object.values(traceData.spans).filter(
      (s) => !s.parentSpanId
    );
    const rootSpan = rootSpans.length > 0 ? rootSpans[0] : undefined;
    const indexData = {
      id: traceData.traceId,
    } as Record<string, string | number>;
    indexData['type'] =
      `${rootSpan?.attributes?.['genkit:metadata:subtype'] || rootSpan?.attributes?.['genkit:type'] || 'UNKNOWN'}`;
    if (rootSpan?.startTime) {
      indexData['start'] = rootSpan.startTime;
    }
    if (rootSpan?.displayName) {
      indexData['name'] = rootSpan.displayName;
    }
    if (rootSpan?.endTime) {
      indexData['end'] = rootSpan.endTime;
    }

    try {
      lockfile.lockSync(lockFile(this.currentIndexFile));

      fs.appendFileSync(
        this.currentIndexFile,
        JSON.stringify(indexData) + '\n'
      );
    } finally {
      lockfile.unlockSync(lockFile(this.currentIndexFile));
    }
  }

  search(query: {
    limit: number;
    startFromIndex?: number;
    filter?: TraceQueryFilter;
  }): IndexSearchResult {
    const idxTxt = fs.readFileSync(this.currentIndexFile, 'utf8');
    const fullData = idxTxt
      .split('\n')
      .map((l) => {
        try {
          return JSON.parse(l);
        } catch {
          return undefined;
        }
      })
      .filter((d) => {
        if (!d) return false;
        if (!query?.filter) return true;
        if (
          query.filter.eq &&
          Object.keys(query.filter.eq).find(
            (k) => d[k] !== query.filter!.eq![k]
          )
        ) {
          return false;
        }
        if (
          query.filter.neq &&
          Object.keys(query.filter.neq).find(
            (k) => d[k] === query.filter!.neq![k]
          )
        ) {
          return false;
        }
        return true;
      })
      .reverse();

    // do pagination
    const startFromIndex = query.startFromIndex ?? 0;

    const result = {
      data: fullData.slice(startFromIndex, startFromIndex + query.limit),
    } as IndexSearchResult;

    // if there are more results, populate stop index.
    if (startFromIndex + query.limit < fullData.length) {
      result.pageLastIndex = startFromIndex + query.limit;
    }

    return result;
  }
}

function lockFile(file: string) {
  return `${file}.lock`;
}

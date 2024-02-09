import * as registry from '../registry';
import logging from '../logging';
import os from 'os'
import fs from 'fs'
import path from 'path'
import crypto from 'crypto'
import { TraceData, TraceDataSchema, TraceQuery, TraceStore } from './types';
import { setGlobalTraceStore } from '../tracing';

/**
 * Configures default trace store to use {@link LocalFileTraceStore}.
 */
export function useDevTraceStore() {
  setGlobalTraceStore(new LocalFileTraceStore());
}

/**
 * Implementation of trace store that persists traces on local disk.
 */
export class LocalFileTraceStore implements TraceStore {
  private readonly storeRoot;

  constructor() {
    var rootHash = crypto.createHash('md5').update(require?.main?.filename || "unknown").digest('hex');
    this.storeRoot = path.resolve(os.tmpdir(), `.genkit/${rootHash}/traces`)
    fs.mkdirSync(this.storeRoot, {recursive: true})
    logging.info("Using DevTraceStore. Root: " + this.storeRoot)
  }

  async load(id: string): Promise<TraceData | undefined> {
    const filePath = path.resolve(this.storeRoot, `${id}`);
    if (!fs.existsSync(filePath)) {
      return undefined;
    }
    const data = fs.readFileSync(filePath, "utf8");
    return TraceDataSchema.parse(JSON.parse(data));
  }

  async save(id: string, trace: TraceData): Promise<void> {
    const existsing = await this.load(id);
    if (existsing) {
      Object.keys(trace.spans).forEach(spanId => existsing.spans[spanId] = trace.spans[spanId])
      existsing.displayName = trace.displayName;
      existsing.startTime = trace.startTime;
      existsing.endTime = trace.endTime;
      trace = existsing;
    }
    logging.debug(`save trace ${id} to ` + path.resolve(this.storeRoot, `${id}`));
    fs.writeFileSync(path.resolve(this.storeRoot, `${id}`), JSON.stringify(trace));
  }

  async list(query?: TraceQuery): Promise<TraceData[]> {
    var files = fs.readdirSync(this.storeRoot);
    files.sort((a, b) => {
      return fs.statSync(path.resolve(this.storeRoot, `${b}`)).mtime.getTime() -
        fs.statSync(path.resolve(this.storeRoot, `${a}`)).mtime.getTime();
    });
    return files.slice(0, query?.limit || 10).map(id => {
      const filePath = path.resolve(this.storeRoot, `${id}`);
      const data = fs.readFileSync(filePath, "utf8");
      return TraceDataSchema.parse(JSON.parse(data));
    })
  }
}

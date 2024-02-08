import { FlowState, FlowStateQuery, FlowStateSchema, FlowStateStore, setGlobalFlowStateStore } from './flowTypes';
import logging from './logging';
import os from 'os'
import fs from 'fs'
import path from 'path'
import crypto from 'crypto'

/**
 * Configures default state store to use {@link DevStateStore}.
 */
export function useDevFlowStateStore() {
  setGlobalFlowStateStore(new LocalFileFlowStateStore());
}

/**
 * Implementation of flow state store that persistes flow state on local disk.
 */
export class LocalFileFlowStateStore implements FlowStateStore {
  private readonly storeRoot;

  constructor() {
    var rootHash = crypto.createHash('md5').update(require?.main?.filename || "unknown").digest('hex');
    this.storeRoot = path.resolve(os.tmpdir(), `.genkit/${rootHash}/flows`)
    fs.mkdirSync(this.storeRoot, {recursive: true})
    logging.info("Using DevFlowStateStore. Root: " + this.storeRoot)
  }

  async load(id: string): Promise<FlowState | undefined> {
    const filePath = path.resolve(os.tmpdir(), `${id}`);
    if (!fs.existsSync(filePath)) {
      return undefined;
    }
    const data = fs.readFileSync(filePath);
    return FlowStateSchema.parse(data);
  }

  async save(id: string, state: FlowState): Promise<void> {
    logging.debug('save flow state ' + id);
    fs.writeFileSync(path.resolve(this.storeRoot, `${id}`), JSON.stringify(state));
  }

  async list(query?: FlowStateQuery): Promise<FlowState[]> {
    var files = fs.readdirSync(this.storeRoot);
    files.sort((a, b) => {
      return fs.statSync(path.resolve(this.storeRoot, `${b}`)).mtime.getTime() -
        fs.statSync(path.resolve(this.storeRoot, `${a}`)).mtime.getTime();
    });
    return files.slice(0, query?.limit || 10).map(id => {
      const filePath = path.resolve(this.storeRoot, `${id}`);
      const data = fs.readFileSync(filePath, "utf8");
      return FlowStateSchema.parse(JSON.parse(data));  
    })
  }
}

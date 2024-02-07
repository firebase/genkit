import fs from 'fs';
import path from 'path';
import { setLogLevel } from './logging';
import * as registry from './registry';
import {
  TraceStore,
  enableTracingAndMetrics,
} from './tracing';
import { Action } from './types';
import { FlowStateStore } from './flowTypes';

let configured = false;
export let config: Config;

// TODO: temporary! make this nice
interface Config {
  tracestore?: TraceStore;
  flowstore?: FlowStateStore;
  enableTracingAndMetrics?: boolean;
  logLevel?: 'fatal' | 'error' | 'warn' | 'info' | 'debug' | 'trace';
  models: Action<any, any, any>[];
}

export function genkitConfig(cfg: Config) {
  config = cfg;
  return config;
}

/**
 * Locates `genkit.conf.js` and configures genkit using the config.
 */
export function initializeGenkit() {
  if (configured) {
    return;
  }
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const config = require(findGenkitConfig()).default as Config;
  if (config.flowstore) {
    registry.register('/flows/stateStore', config.flowstore);
  }
  if (config.tracestore) {
    registry.register('/flows/traceStore', config.tracestore);
  }
  if (config.enableTracingAndMetrics) {
    enableTracingAndMetrics();
  }
  if (config.logLevel) {
    setLogLevel(config.logLevel);
  }
  configured = true;
}

function findGenkitConfig() {
  let current = require?.main?.filename;
  if (!current) {
    throw new Error('Unable to resolve package root');
  }
  while (path.resolve(current, '..') !== current) {
    if (fs.existsSync(path.resolve(current, 'genkit.conf.js'))) {
      return path.resolve(current, 'genkit.conf.js');
    }
    current = path.resolve(current, '..');
  }
  throw new Error(
    'Unable to find genkit.conf.js in any of the parent directories.'
  );
}

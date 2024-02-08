import fs from 'fs';
import path from 'path';
import logging, { setLogLevel } from './logging';
import * as registry from './registry';
import {
  enableTracingAndMetrics,
} from './tracing';
import { Action } from './types';
import { Plugin } from './plugin';

export * from "./plugin"

let configured = false;
export let config: Config;

// TODO: temporary! make this nice
interface Config {
  plugins?: Plugin[],
  tracestore?: string;
  flowstore?: string;
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
    logging.warn("initializeGenkit was already called")
    return;
  }
  const configPath = findGenkitConfig();
  if (!configPath) {
    logging.warn(
      'Unable to find genkit.conf.js in any of the parent directories.'
    );  
    return;
  }
  const config = require(configPath).default as Config;
  config.plugins?.forEach(plugin => {
    if (plugin.provides?.flowStateStore) {
      logging.debug(`configuring plugin: ${plugin.name}, flowStateStore: ${plugin.provides.flowStateStore.id}`)
      registry.register(`/flowStateStore/${plugin.provides.flowStateStore.id}`, plugin.provides.flowStateStore.value);
    }
    if (plugin.provides?.traceStore) {
      logging.debug(`configuring plugin: ${plugin.name}, traceStore: ${plugin.provides.traceStore.id}`)
      registry.register(`/traceStore/${plugin.provides.traceStore.id}`, plugin.provides.traceStore.value);
    }
    plugin.provides?.models?.forEach(model => {
      registry.registerAction('model', model.name, model)
    })
    plugin.provides?.embedders?.forEach(embedder => {
      registry.registerAction('embedder', embedder.name, embedder)
    })
    plugin.provides?.retrievers?.forEach(retriever => {
      registry.registerAction('retriever', retriever.name, retriever)
    })
    plugin.provides?.indexers?.forEach(indexer => {
      registry.registerAction('indexer', indexer.name, indexer)
    })
  })
  if (config.flowstore) {
    registry.register('/flows/stateStorePlugin', config.flowstore);
  }
  if (config.tracestore) {
    registry.register('/trace/storePlugin', config.tracestore);
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
  return undefined;
}

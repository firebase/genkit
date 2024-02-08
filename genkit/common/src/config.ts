import fs from 'fs';
import path from 'path';
import logging, { setLogLevel } from './logging';
import * as registry from './registry';
import {
  TraceStore,
  enableTracingAndMetrics, getGlobalTraceStore, setGlobalTraceStore, useDevTraceStore,
} from './tracing';
import { Action } from './types';
import { Plugin } from './plugin';
import { FlowStateStore, getGlobalFlowStateStore, setGlobalFlowStateStore } from './flowTypes';
import { useDevFlowStateStore } from './flowLocalFileStore';

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
  if (!config.flowstore) {
    logging.warn("flowstore is not specified in the config file, using dev store.")
  }
  if (!config.tracestore) {
    logging.warn("tracestore is not specified in the config file, using dev store.")
  }
  if (isDevMode()) {
    // In dev mode we always use dev stores!
    useDevFlowStateStore();
    useDevTraceStore();
  } else {
    if (config.flowstore) {
      setGlobalFlowStateStore(lookupConfguredFlowStateStore(config.flowstore))
    } else {
      // if no prod store configured we default to dev. Logging warning above.
      useDevFlowStateStore();
    }
    if (config.tracestore) {
      setGlobalTraceStore(lookupConfiguredTraceStore(config.tracestore))
    } else {
      // if no prod store configured we default to dev. Logging warning above.
      useDevTraceStore();
    }
  }
  if (config.enableTracingAndMetrics) {
    enableTracingAndMetrics();
  }
  if (config.logLevel) {
    setLogLevel(config.logLevel);
  }
  configured = true;
}

function isDevMode() {
  return !!process.env.GENKIT_START_REFLECTION_API;
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

/**
 * Looks up configured flow state store provided by the specified plugin.
 */
function lookupConfguredFlowStateStore(pluginName: string): FlowStateStore {
  const plugin = config.plugins?.find(p => p.name === pluginName);
  if (!plugin) {
    throw new Error("Unable to resolve plugin name: " + pluginName);
  }
  const provider = plugin.provides.flowStateStore;
  if (!provider) {
    throw new Error("Unable to resolve provider `flowStateStore` for plugin: " + pluginName);
  }
  const flowStateStore = registry.lookup(`/flowStateStore/${provider.id}`)
  if (!flowStateStore) {
    throw new Error("Unable to resolve flowStateStore for plugin: " + pluginName);
  }
  return flowStateStore as FlowStateStore;
}

/**
 * Looks up configured trace store provided by the specified plugin.
 */
function lookupConfiguredTraceStore(pluginName: string): TraceStore {
  const plugin = config.plugins?.find(p => p.name === pluginName);
  if (!plugin) {
    throw new Error("Unable to resolve plugin name: " + pluginName);
  }
  const provider = plugin.provides.traceStore;
  if (!provider) {
    throw new Error("Unable to resolve provider `traceStore` for plugin: " + pluginName);
  }
  const tracestore = registry.lookup(`/traceStore/${provider.id}`)
  if (!tracestore) {
    throw new Error("Unable to resolve tracestore for plugin: " + pluginName);
  }
  return tracestore as TraceStore;
}

let prodFlowStateStore: FlowStateStore;

/**
 * Returns a flow state store instance for the provided environment. In 'dev' it's assumed to be
 * local file store, and in prod it looks up what is set in the config.
 */
export function getFlowStateStore(env: 'dev' | 'prod'): FlowStateStore {
  if (env === 'dev' || !config.flowstore) {
    // This assumes that the dev UI will only run in dev env, so global store must be dev.
    return getGlobalFlowStateStore()
  }
  if (prodFlowStateStore) {
    return prodFlowStateStore;
  }
  const pluginName = config.flowstore;
  prodFlowStateStore = lookupConfguredFlowStateStore(pluginName);
  return prodFlowStateStore ;
}

let prodTracestore: TraceStore;

/**
 * Returns a trace store instance for the provided environment. In 'dev' it's assumed to be
 * local file store, and in prod it looks up what is set in the config.
 */
export function getTraceStore(env: "dev" | "prod"): TraceStore {
  if (env === 'dev' || !config.tracestore) {
    // This assumes that the dev UI will only run in dev env, so global store must be dev.
    return getGlobalTraceStore()
  }
  if (prodTracestore) {
    return prodTracestore;
  }
  const pluginName = config.tracestore;
  prodTracestore = lookupConfiguredTraceStore(pluginName);
  return prodTracestore;
}
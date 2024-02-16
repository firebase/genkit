import fs from 'fs';
import path from 'path';
import { FlowStateStore } from './flowTypes.js';
import { LocalFileFlowStateStore } from './localFileFlowStateStore.js';
import logging, { setLogLevel } from './logging.js';
import { PluginProvider } from './plugin.js';
import * as registry from './registry.js';
import { TraceStore, enableTracingAndMetrics } from './tracing.js';
import { LocalFileTraceStore } from './tracing/localFileTraceStore.js';

export * from './plugin.js';

export let config: Config;
export interface ConfigOptions {
  plugins?: PluginProvider[];
  traceStore?: string;
  flowStateStore?: string;
  enableTracingAndMetrics?: boolean;
  logLevel?: 'fatal' | 'error' | 'warn' | 'info' | 'debug' | 'trace';
}

class Config {
  /** Developer-configured options. */
  readonly options: ConfigOptions;
  readonly configuredEnvs = new Set<string>(['dev']);

  constructor(options: ConfigOptions) {
    this.options = options;
    this.configure();
  }

  /**
   * Returns a flow state store instance for the running environment.
   * If no store is configured, this will warn and default to `dev`.
   */
  public getFlowStateStore(): FlowStateStore {
    const env = getCurrentEnv();
    let flowStateStore = registry.lookupFlowStateStore(env);
    if (!flowStateStore && env !== 'dev') {
      flowStateStore = registry.lookupFlowStateStore('dev');
      logging.warn(
        `No flow state store configured for \`${env}\` environment. Defaulting to \`dev\` store.`
      );
    }
    if (!flowStateStore) {
      throw new Error('No flow store is configured.');
    }
    return flowStateStore;
  }

  /**
   * Returns a trace store instance for the running environment.
   * If no store is configured, this will warn and default to `dev`.
   */
  public getTraceStore(): TraceStore {
    const env = getCurrentEnv();
    let traceStore = registry.lookupTraceStore(env);
    if (!traceStore && env !== 'dev') {
      traceStore = registry.lookupTraceStore('dev');
      logging.warn(
        `No trace store configured for \`${env}\` environment. Defaulting to \`dev\` store.`
      );
    }
    if (!traceStore) {
      throw new Error('No trace store is configured.');
    }
    return traceStore;
  }

  /**
   * Configures the system.
   */
  private configure() {
    this.options.plugins?.forEach((plugin) => {
      logging.debug(`Registering plugin ${plugin.name}...`);
      registry.registerPluginProvider(plugin.name, {
        name: plugin.name,
        initializer() {
          logging.debug(`Initializing plugin ${plugin.name}:`);
          const initializedPlugin = plugin.initializer();
          initializedPlugin.models?.forEach((model) => {
            logging.debug(`  - Model: ${model.__action.name}`);
            registry.registerAction('model', model.__action.name, model);
          });
          initializedPlugin.embedders?.forEach((embedder) => {
            logging.debug(`  - Embedder: ${embedder.__action.name}`);
            registry.registerAction(
              'embedder',
              embedder.__action.name,
              embedder
            );
          });
          initializedPlugin.retrievers?.forEach((retriever) => {
            logging.debug(`  - Retriever: ${retriever.__action.name}`);
            registry.registerAction(
              'retriever',
              retriever.__action.name,
              retriever
            );
          });
          initializedPlugin.indexers?.forEach((indexer) => {
            logging.debug(`  - Indexer: ${indexer.__action.name}`);
            registry.registerAction('indexer', indexer.__action.name, indexer);
          });
          return initializedPlugin;
        },
      });
    });

    logging.debug('Registering flow state stores...');
    registry.registerFlowStateStore('dev', () => new LocalFileFlowStateStore());
    if (this.options.flowStateStore) {
      const flowStorePluginName = this.options.flowStateStore;
      logging.debug(`  - prod: ${flowStorePluginName}`);
      this.configuredEnvs.add('prod');
      registry.registerFlowStateStore('prod', () =>
        this.resolveFlowStateStore(flowStorePluginName)
      );
    } else {
      logging.warn(
        '`flowStateStore` is not specified in the config; defaulting to dev store.'
      );
    }

    logging.debug('Registering trace stores...');
    registry.registerTraceStore('dev', () => new LocalFileTraceStore());
    if (this.options.traceStore) {
      const traceStorePluginName = this.options.traceStore;
      logging.debug(`  - prod: ${traceStorePluginName}`);
      this.configuredEnvs.add('prod');
      registry.registerTraceStore('prod', () =>
        this.resolveTraceStore(traceStorePluginName)
      );
    } else {
      logging.warn(
        '`traceStore` is not specified in the config; defaulting to dev store.'
      );
    }

    if (this.options.logLevel) {
      setLogLevel(this.options.logLevel);
    }
  }

  /**
   * Resolves flow state store provided by the specified plugin.
   */
  private resolveFlowStateStore(pluginName: string) {
    const plugin = registry.initializePlugin(pluginName);
    const provider = plugin?.flowStateStore;
    if (!provider) {
      throw new Error(
        'Unable to resolve provided `flowStateStore` for plugin: ' + pluginName
      );
    }
    return provider.value;
  }

  /**
   * Resolves trace store provided by the specified plugin.
   */
  private resolveTraceStore(pluginName: string) {
    const plugin = registry.initializePlugin(pluginName);
    const provider = plugin?.traceStore;
    if (!provider) {
      throw new Error(
        'Unable to resolve provided `traceStore` for plugin: ' + pluginName
      );
    }
    return provider.value;
  }
}

/**
 * Configures Genkit with a set of options. This should be called from `genkit.config.js`.
 */
export function configureGenkit(options: ConfigOptions): Config {
  if (config) {
    throw new Error('configureGenkit was already called');
  }
  config = new Config(options);
  if (options.enableTracingAndMetrics) {
    enableTracingAndMetrics();
  }
  return config;
}

/**
 * Locates `genkit.conf.js` and loads the file so that the config can be registered.
 */
export function initializeGenkit(cfg?: Config) {
  // Already initialized.
  if (config || cfg) {
    return;
  }
  const configPath = findGenkitConfig();
  if (!configPath) {
    throw Error(
      'Unable to find genkit.conf.js in any of the parent directories.'
    );
  }
  // Loading the config file will automatically register the config.
  require(configPath);
}

/**
 * @returns The current environment that the app code is running in.
 */
export function getCurrentEnv(): string {
  return process.env.GENKIT_ENV || 'prod';
}

/**
 * Locates `genkit.conf.js` and returns the path.
 */
function findGenkitConfig() {
  let current = require?.main?.filename;
  if (!current) {
    throw new Error('Unable to resolve package root.');
  }
  while (path.resolve(current, '..') !== current) {
    if (fs.existsSync(path.resolve(current, 'genkit.conf.js'))) {
      return path.resolve(current, 'genkit.conf.js');
    }
    current = path.resolve(current, '..');
  }
  return undefined;
}

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

import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import fs from 'fs';
import path from 'path';
import { FlowStateStore } from './flowTypes';
import { LocalFileFlowStateStore } from './localFileFlowStateStore';
import logging, { setLogLevel } from './logging';
import { PluginProvider } from './plugin';
import * as registry from './registry';
import { AsyncProvider } from './registry';
import { TelemetryConfig, TelemetryOptions } from './telemetryTypes';
import { TraceStore, enableTracingAndMetrics } from './tracing';
import { LocalFileTraceStore } from './tracing/localFileTraceStore';

export * from './plugin.js';

export let config: Config;
export interface ConfigOptions {
  plugins?: PluginProvider[];
  traceStore?: string;
  flowStateStore?: string;
  enableTracingAndMetrics?: boolean;
  logLevel?: 'fatal' | 'error' | 'warn' | 'info' | 'debug' | 'trace';
  promptDir?: string;
  telemetry?: TelemetryOptions;
}

class Config {
  /** Developer-configured options. */
  readonly options: ConfigOptions;
  readonly configuredEnvs = new Set<string>(['dev']);

  private telemetryConfig: AsyncProvider<TelemetryConfig>;

  constructor(options: ConfigOptions) {
    this.options = options;
    this.telemetryConfig = async () =>
      <TelemetryConfig>{
        getConfig() {
          return {} as Partial<NodeSDKConfiguration>;
        },
      };
    this.configure();
  }

  /**
   * Returns a flow state store instance for the running environment.
   * If no store is configured, this will warn and default to `dev`.
   */
  public async getFlowStateStore(): Promise<FlowStateStore> {
    const env = getCurrentEnv();
    let flowStateStore = await registry.lookupFlowStateStore(env);
    if (!flowStateStore && env !== 'dev') {
      flowStateStore = await registry.lookupFlowStateStore('dev');
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
  public async getTraceStore(): Promise<TraceStore> {
    const env = getCurrentEnv();
    let traceStore = await registry.lookupTraceStore(env);
    if (!traceStore && env !== 'dev') {
      traceStore = await registry.lookupTraceStore('dev');
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
   * Returns the configuration for exporting Telemetry data for the current
   * environment.
   */
  public getTelemetryConfig(): Promise<TelemetryConfig> {
    return this.telemetryConfig();
  }

  /**
   * Configures the system.
   */
  private configure() {
    if (this.options.logLevel) {
      setLogLevel(this.options.logLevel);
    }
    this.options.plugins?.forEach((plugin) => {
      logging.debug(`Registering plugin ${plugin.name}...`);
      registry.registerPluginProvider(plugin.name, {
        name: plugin.name,
        async initializer() {
          logging.info(`Initializing plugin ${plugin.name}:`);
          return await plugin.initializer();
        },
      });
    });

    logging.debug('Registering flow state stores...');
    registry.registerFlowStateStore(
      'dev',
      async () => new LocalFileFlowStateStore()
    );
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
    registry.registerTraceStore('dev', async () => new LocalFileTraceStore());
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

    logging.debug('Registering telemetry exporters...');
    if (this.options.telemetry) {
      const telemetryPluginName = this.options.telemetry.instrumentation;
      logging.debug(`  - all environments: ${telemetryPluginName}`);
      this.telemetryConfig = async () =>
        this.resolveTelemetryConfig(telemetryPluginName);
    }
  }

  /**
   * Resolves flow state store provided by the specified plugin.
   */
  private async resolveFlowStateStore(pluginName: string) {
    const plugin = await registry.initializePlugin(pluginName);
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
  private async resolveTraceStore(pluginName: string) {
    const plugin = await registry.initializePlugin(pluginName);
    const provider = plugin?.traceStore;
    if (!provider) {
      throw new Error(
        'Unable to resolve provided `traceStore` for plugin: ' + pluginName
      );
    }
    return provider.value;
  }

  /**
   * Resolves the telemetry configuration provided by the specified plugin.
   */
  private async resolveTelemetryConfig(pluginName: string) {
    const plugin = await registry.initializePlugin(pluginName);
    const provider = plugin?.telemetry;

    if (!provider) {
      throw new Error(
        'Unable to resolve provider `telemetry` for plugin: ' + pluginName
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

/** Whether current env is `dev`. */
export function isDevEnv(): boolean {
  return getCurrentEnv() === 'dev';
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

export function __hardResetConfigForTesting() {
  (config as any) = undefined;
}

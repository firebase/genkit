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
import { FlowStateStore } from './flowTypes.js';
import { LocalFileFlowStateStore } from './localFileFlowStateStore.js';
import { logger } from './logging.js';
import { PluginProvider } from './plugin.js';
import * as registry from './registry.js';
import { AsyncProvider } from './registry.js';
import {
  LoggerConfig,
  TelemetryConfig,
  TelemetryOptions,
} from './telemetryTypes.js';
import { TraceStore, enableTracingAndMetrics } from './tracing.js';
import { LocalFileTraceStore } from './tracing/localFileTraceStore.js';

export * from './plugin.js';

export let config: Config;
export interface ConfigOptions {
  plugins?: PluginProvider[];
  traceStore?: string;
  flowStateStore?: string;
  enableTracingAndMetrics?: boolean;
  logLevel?: 'error' | 'warn' | 'info' | 'debug';
  promptDir?: string;
  telemetry?: TelemetryOptions;
}

class Config {
  /** Developer-configured options. */
  readonly options: ConfigOptions;
  readonly configuredEnvs = new Set<string>(['dev']);

  private telemetryConfig: AsyncProvider<TelemetryConfig>;
  private loggerConfig?: AsyncProvider<LoggerConfig>;

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
      logger.warn(
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
      logger.warn(
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
      logger.setLogLevel(this.options.logLevel);
    }

    this.options.plugins?.forEach((plugin) => {
      logger.debug(`Registering plugin ${plugin.name}...`);
      registry.registerPluginProvider(plugin.name, {
        name: plugin.name,
        async initializer() {
          logger.info(`Initializing plugin ${plugin.name}:`);
          return await plugin.initializer();
        },
      });
    });

    if (this.options.telemetry?.logger) {
      const loggerPluginName = this.options.telemetry.logger;
      logger.debug('Registering logging exporters...');
      logger.debug(`  - all environments: ${loggerPluginName}`);
      this.loggerConfig = async () =>
        this.resolveLoggerConfig(loggerPluginName);
    }

    if (this.options.telemetry?.instrumentation) {
      const telemetryPluginName = this.options.telemetry.instrumentation;
      logger.debug('Registering telemetry exporters...');
      logger.debug(`  - all environments: ${telemetryPluginName}`);
      this.telemetryConfig = async () =>
        this.resolveTelemetryConfig(telemetryPluginName);
    }

    logger.debug('Registering flow state stores...');
    registry.registerFlowStateStore(
      'dev',
      async () => new LocalFileFlowStateStore()
    );
    if (this.options.flowStateStore) {
      const flowStorePluginName = this.options.flowStateStore;
      logger.debug(`  - prod: ${flowStorePluginName}`);
      this.configuredEnvs.add('prod');
      registry.registerFlowStateStore('prod', () =>
        this.resolveFlowStateStore(flowStorePluginName)
      );
    } else {
      logger.warn(
        '`flowStateStore` is not specified in the config; defaulting to dev store.'
      );
    }

    logger.debug('Registering trace stores...');
    registry.registerTraceStore('dev', async () => new LocalFileTraceStore());
    if (this.options.traceStore) {
      const traceStorePluginName = this.options.traceStore;
      logger.debug(`  - prod: ${traceStorePluginName}`);
      this.configuredEnvs.add('prod');
      registry.registerTraceStore('prod', () =>
        this.resolveTraceStore(traceStorePluginName)
      );
    } else {
      logger.warn(
        '`traceStore` is not specified in the config; defaulting to dev store.'
      );
    }
  }

  /**
   * Sets up the tracing and logging as configured.
   *
   * Note: the logging configuration must come after tracing has been enabled to
   * ensure that all tracing instrumentations are applied.
   * See limitations described here:
   * https://github.com/open-telemetry/opentelemetry-js/tree/main/experimental/packages/opentelemetry-instrumentation#limitations
   */
  async setupTracingAndLogging() {
    if (this.options.enableTracingAndMetrics) {
      enableTracingAndMetrics(
        await this.getTelemetryConfig(),
        await this.getTraceStore()
      );
    }
    if (this.loggerConfig) {
      logger.init(await this.loggerConfig());
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
    const provider = plugin?.telemetry?.instrumentation;

    if (!provider) {
      throw new Error(
        'Unable to resolve provider `telemetry.instrumentation` for plugin: ' +
          pluginName
      );
    }
    return provider.value;
  }

  /**
   * Resolves the logging configuration provided by the specified plugin.
   */
  private async resolveLoggerConfig(pluginName: string) {
    const plugin = await registry.initializePlugin(pluginName);
    const provider = plugin?.telemetry?.logger;

    if (!provider) {
      throw new Error(
        'Unable to resolve provider `telemetry.logger` for plugin: ' +
          pluginName
      );
    }
    return provider.value;
  }
}

/**
 * Configures Genkit with a set of options. This should be called from `genkit.configig.js`.
 */
export function configureGenkit(options: ConfigOptions): Config {
  if (config) {
    logger.warn('configureGenkit was already called');
  }
  config = new Config(options);
  config.setupTracingAndLogging();
  return config;
}

/**
 * Locates `genkit.config.js` and loads the file so that the config can be registered.
 */
export function initializeGenkit(cfg?: Config) {
  // Already initialized.
  if (config || cfg) {
    return;
  }
  const configPath = findGenkitConfig();
  if (!configPath) {
    throw Error(
      'Unable to find genkit.config.js in any of the parent directories.'
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
 * Locates `genkit.config.js` and returns the path.
 */
function findGenkitConfig() {
  let current = require?.main?.filename;
  if (!current) {
    throw new Error('Unable to resolve package root.');
  }
  while (path.resolve(current, '..') !== current) {
    if (fs.existsSync(path.resolve(current, 'genkit.config.js'))) {
      return path.resolve(current, 'genkit.config.js');
    }
    current = path.resolve(current, '..');
  }
  return undefined;
}

export function __hardResetConfigForTesting() {
  (config as any) = undefined;
}

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
import z from 'zod';
import {
  CallableFlow,
  defineFlow,
  defineStreamingFlow,
  Flow,
  FlowConfig,
  FlowFn,
  FlowServer,
  FlowServerOptions,
  StreamableFlow,
  StreamingFlowConfig,
} from './flow.js';
import { logger } from './logging.js';
import { PluginProvider } from './plugin.js';
import { ReflectionServer } from './reflection.js';
import * as registry from './registry.js';
import { AsyncProvider, Registry, runWithRegistry } from './registry.js';
import {
  LoggerConfig,
  TelemetryConfig,
  TelemetryOptions,
} from './telemetryTypes.js';
import { cleanUpTracing, enableTracingAndMetrics } from './tracing.js';
import { isDevEnv } from './utils.js';

/**
 * Options for initializing Genkit.
 */
export interface GenkitOptions {
  /** List of plugins to load. */
  plugins?: PluginProvider[];
  /** Name of the trace store to use. If not specified, a dev trace store will be used. The trace store must be registered in the config. */
  traceStore?: string;
  /** Name of the flow state store to use. If not specified, a dev flow state store will be used. The flow state store must be registered in the config. */
  flowStateStore?: string;
  /** Whether to enable tracing and metrics. */
  enableTracingAndMetrics?: boolean;
  /** Level at which to log messages.*/
  logLevel?: 'error' | 'warn' | 'info' | 'debug';
  /** Directory where dotprompts are stored. */
  promptDir?: string;
  // FIXME: Telemetry cannot be scoped to a single Genkit instance.
  /** Telemetry configuration. */
  telemetry?: TelemetryOptions;
  /** Default model to use if no model is specified. */
  defaultModel?: {
    /** Name of the model to use. */
    name: string | { name: string };
    /** Configuration for the model. */
    config?: Record<string, any>;
  };
  // FIXME: This will not actually expose any flows. It needs a new mechanism for exposing endpoints.
  /** Configuration for the flow server. Server will be started if value is true or a configured object. */
  flowServer?: FlowServerOptions | boolean;
}

/**
 * `Genkit` encapsulates a single Genkit instance including {@link Registry}, {@link ReflectionServer}, flow server, and configuration.
 *
 * Registry keeps track of actions, flows, tools, and many other components. Reflection server exposes an API to inspect the registry and trigger executions of actions in the registry. Flow server exposes flows as HTTP endpoints for production use.
 *
 * There may be multiple Genkit instances in a single codebase.
 */
export class Genkit {
  /** Developer-configured options. */
  readonly options: GenkitOptions;
  /** Environments that have been configured (at minimum dev). */
  readonly configuredEnvs = new Set<string>(['dev']);
  /** Registry instance that is exclusively modified by this Genkit instance. */
  readonly registry: Registry;

  /** Async provider for the telemtry configuration. */
  private telemetryConfig: AsyncProvider<TelemetryConfig>;
  /** Async provider for the logger configuration. */
  private loggerConfig?: AsyncProvider<LoggerConfig>;
  /** Reflection server for this registry. May be null if not started. */
  private reflectionServer: ReflectionServer | null = null;
  /** Flow server. May be null if the flow server is not enabled in configuration or not started. */
  private flowServer: FlowServer | null = null;
  /** List of flows that have been registered in this instance. */
  private registeredFlows: Flow<any, any, any>[] = [];

  constructor(options?: GenkitOptions) {
    this.options = options || {};
    this.telemetryConfig = async () =>
      <TelemetryConfig>{
        getConfig() {
          return {} as Partial<NodeSDKConfiguration>;
        },
      };
    this.registry = new Registry();
    this.configure();
    if (isDevEnv()) {
      this.reflectionServer = new ReflectionServer(this.registry, {
        configuredEnvs: [...this.configuredEnvs],
      });
      this.reflectionServer.start();
    }
    if (this.options.flowServer) {
      const flowServerOptions =
        typeof this.options.flowServer === 'object'
          ? this.options.flowServer
          : undefined;
      this.flowServer = new FlowServer(this.registry, flowServerOptions);
      this.flowServer.start();
    }
  }

  /**
   * Defines a flow.
   */
  defineFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(config: FlowConfig<I, O>, fn: FlowFn<I, O>): CallableFlow<I, O> {
    const flow = runWithRegistry(this.registry, () => defineFlow(config, fn));
    this.registeredFlows.push(flow.flow);
    return flow;
  }

  /**
   * Defines a streaming flow.
   */
  defineStreamingFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    S extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    config: StreamingFlowConfig<I, O, S>,
    fn: FlowFn<I, O, S>
  ): StreamableFlow<I, O, S> {
    const flow = runWithRegistry(this.registry, () =>
      defineStreamingFlow(config, fn)
    );
    this.registeredFlows.push(flow.flow);
    return flow;
  }

  /**
   * Returns the configuration for exporting Telemetry data for the current
   * environment.
   */
  getTelemetryConfig(): Promise<TelemetryConfig> {
    return this.telemetryConfig();
  }

  /**
   * Configures the Genkit instance.
   */
  private configure() {
    if (this.options.logLevel) {
      logger.setLogLevel(this.options.logLevel);
    }

    this.options.plugins?.forEach((plugin) => {
      logger.debug(`Registering plugin ${plugin.name}...`);
      const activeRegistry = this.registry;
      activeRegistry.registerPluginProvider(plugin.name, {
        name: plugin.name,
        async initializer() {
          logger.info(`Initializing plugin ${plugin.name}:`);
          return runWithRegistry(activeRegistry, () => plugin.initializer());
        },
      });
    });

    if (this.options.telemetry?.logger) {
      const loggerPluginName = this.options.telemetry.logger;
      logger.debug('Registering logging exporters...');
      logger.debug(`  - all environments: ${loggerPluginName}`);
      this.loggerConfig = async () =>
        runWithRegistry(this.registry, () =>
          this.resolveLoggerConfig(loggerPluginName)
        );
    }

    if (this.options.telemetry?.instrumentation) {
      const telemetryPluginName = this.options.telemetry.instrumentation;
      logger.debug('Registering telemetry exporters...');
      logger.debug(`  - all environments: ${telemetryPluginName}`);
      this.telemetryConfig = async () =>
        runWithRegistry(this.registry, () =>
          this.resolveTelemetryConfig(telemetryPluginName)
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
      enableTracingAndMetrics(await this.getTelemetryConfig());
    }
    if (this.loggerConfig) {
      logger.init(await this.loggerConfig());
    }
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

  /**
   * Stops all servers.
   */
  async stopServers() {
    await Promise.all([this.reflectionServer?.stop(), this.flowServer?.stop()]);
    this.reflectionServer = null;
    this.flowServer = null;
  }
}

/**
 * Initializes Genkit with a set of options.
 *
 * This will create a new Genkit registry, register the provided plugins, stores, and other configuration. This
 * should be called before any flows are registered.
 */
export function genkit(options: GenkitOptions): Genkit {
  const genkit = new Genkit(options);
  genkit.setupTracingAndLogging();
  return genkit;
}

process.on('SIGTERM', async () => {
  logger.debug('Received SIGTERM. Shutting down all Genkit servers...');
  await Promise.all([
    ReflectionServer.stopAll(),
    FlowServer.stopAll(),
    cleanUpTracing(),
  ]);
  process.exit(0);
});

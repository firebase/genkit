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
  BaseDataPointSchema,
  definePrompt,
  defineTool,
  Document,
  embed,
  EmbedderParams,
  Embedding,
  EvalResponses,
  evaluate,
  EvaluatorParams,
  generate,
  GenerateOptions,
  GenerateResponse,
  generateStream,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  index,
  IndexerParams,
  PromptAction,
  PromptConfig,
  PromptFn,
  RankedDocument,
  rerank,
  RerankerParams,
  retrieve,
  RetrieverParams,
  ToolAction,
  ToolConfig,
} from '@genkit-ai/ai';
import {
  CallableFlow,
  defineFlow,
  defineJsonSchema,
  defineSchema,
  defineStreamingFlow,
  Flow,
  FlowConfig,
  FlowFn,
  FlowServer,
  FlowServerOptions,
  isDevEnv,
  JSONSchema,
  LoggerConfig,
  PluginProvider,
  ReflectionServer,
  StreamableFlow,
  StreamingFlowConfig,
  TelemetryConfig,
  TelemetryOptions,
  z,
} from '@genkit-ai/core';
import * as registry from '@genkit-ai/core/registry';
import {
  defineDotprompt,
  Dotprompt,
  prompt,
  PromptMetadata,
} from '@genkit-ai/dotprompt';
import { NodeSDKConfiguration } from '@opentelemetry/sdk-node';
import { logger } from './logging.js';
import { AsyncProvider, Registry, runWithRegistry } from './registry.js';
import { cleanUpTracing, enableTracingAndMetrics } from './tracing.js';
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
  // FIXME: Default model is not currently supported since the switch to non-global registry.
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
 * `Genkit` encapsulates a single Genkit instance including the {@link Registry}, {@link ReflectionServer}, {@link FlowServer}, and configuration.
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
   * Defines and registers a non-streaming flow.
   *
   * @todo TODO: Improve this documentation (show snippets, etc).
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
   * Defines and registers a streaming flow.
   *
   * @todo TODO: Improve this documentation (show snippetss, etc).
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
   * Defines and registers a tool.
   *
   * Tools can be passed to models by name or value during `generate` calls to be called automatically based on the prompt and situation.
   */
  defineTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    config: ToolConfig<I, O>,
    fn: (input: z.infer<I>) => Promise<z.infer<O>>
  ): ToolAction<I, O> {
    return runWithRegistry(this.registry, () => defineTool(config, fn));
  }

  /**
   * Defines and registers a schema from a Zod schema.
   *
   * Defined schemas can be referenced by `name` in prompts in place of inline schemas.
   */
  defineSchema<T extends z.ZodTypeAny>(name: string, schema: T): T {
    runWithRegistry(this.registry, () => defineSchema(name, schema));
    return schema;
  }

  /**
   * Defines and registers a schema from a JSON schema.
   *
   * Defined schemas can be referenced by `name` in prompts in place of inline schemas.
   */
  defineJsonSchema(name: string, jsonSchema: JSONSchema) {
    runWithRegistry(this.registry, () => defineJsonSchema(name, jsonSchema));
    return jsonSchema;
  }

  /**
   * Looks up a prompt by `name` and optional `variant`.
   *
   * @todo TODO: Show an example of a name and variant.
   */
  prompt<Variables = unknown>(
    name: string,
    options?: { variant?: string }
  ): Promise<Dotprompt<Variables>> {
    return runWithRegistry(this.registry, () => prompt(name, options));
  }

  /**
   * Defines and registers a dotprompt.
   *
   * This replaces defining and importing a .dotprompt file.
   *
   * @todo TODO: Improve this documentation (show an example, etc).
   */
  defineDotprompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions>,
    template: string
  ): Dotprompt<z.infer<I>> {
    return runWithRegistry(this.registry, () =>
      defineDotprompt(options, template)
    );
  }

  /**
   * Defines and registers a prompt action.
   */
  definePrompt<I extends z.ZodTypeAny = z.ZodTypeAny>(
    config: PromptConfig<I>,
    fn: PromptFn<I>
  ): PromptAction<I> {
    return runWithRegistry(this.registry, () => definePrompt(config, fn));
  }

  /**
   * Embeds the given `content` using the specified `embedder`.
   */
  embed<CustomOptions extends z.ZodTypeAny>(
    params: EmbedderParams<CustomOptions>
  ): Promise<Embedding> {
    return runWithRegistry(this.registry, () => embed(params));
  }

  /**
   * Evaluates the given `dataset` using the specified `evaluator`.
   */
  evaluate<
    DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(params: EvaluatorParams<DataPoint, CustomOptions>): Promise<EvalResponses> {
    return runWithRegistry(this.registry, () => evaluate(params));
  }

  /**
   * Reranks documents from a {@link RerankerArgument} based on the provided query.
   */
  rerank<CustomOptions extends z.ZodTypeAny>(
    params: RerankerParams<CustomOptions>
  ): Promise<Array<RankedDocument>> {
    return runWithRegistry(this.registry, () => rerank(params));
  }

  /**
   * Indexes `documents` using the provided `indexer`.
   */
  index<CustomOptions extends z.ZodTypeAny>(
    params: IndexerParams<CustomOptions>
  ): Promise<void> {
    return runWithRegistry(this.registry, () => index(params));
  }

  /**
   * Retrieves documents from the `retriever` based on the provided `query`.
   */
  retrieve<CustomOptions extends z.ZodTypeAny>(
    params: RetrieverParams<CustomOptions>
  ): Promise<Array<Document>> {
    return runWithRegistry(this.registry, () => retrieve(params));
  }

  /**
   * Generate calls a generative model based on the provided prompt and configuration. If
   * `history` is provided, the generation will include a conversation history in its
   * request. If `tools` are provided, the generate method will automatically resolve
   * tool calls returned from the model unless `returnToolRequests` is set to `true`.
   *
   * See {@link GenerateOptions} for detailed information about available options.
   */
  generate<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options:
      | GenerateOptions<O, CustomOptions>
      | PromiseLike<GenerateOptions<O, CustomOptions>>
  ): Promise<GenerateResponse<z.infer<O>>> {
    return runWithRegistry(this.registry, () => generate(options));
  }

  /**
   * Generates a stream of responses from a generative model based on the provided prompt
   * and configuration. If `history` is provided, the generation will include a conversation
   * history in its request. If `tools` are provided, the generate method will automatically
   * resolve tool calls returned from the model unless `returnToolRequests` is set to `true`.
   * tool calls returned from the model unless `returnToolRequests` is set to `true`.
   *
   * See {@link GenerateStreamOptions} for detailed information about available options.
   */
  generateStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options:
      | GenerateStreamOptions<O, CustomOptions>
      | PromiseLike<GenerateStreamOptions<O, CustomOptions>>
  ): Promise<GenerateStreamResponse<z.infer<O>>> {
    return runWithRegistry(this.registry, () => generateStream(options));
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

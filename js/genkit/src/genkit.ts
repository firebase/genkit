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
  GenerateRequest,
  GenerateResponse,
  GenerateResponseData,
  generateStream,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  index,
  IndexerParams,
  ModelArgument,
  ModelReference,
  PromptAction,
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
  PluginProvider,
  ReflectionServer,
  StreamableFlow,
  StreamingCallback,
  StreamingFlowConfig,
  z,
} from '@genkit-ai/core';
import {
  defineDotprompt,
  Dotprompt,
  prompt,
  PromptGenerateOptions,
  PromptMetadata,
} from '@genkit-ai/dotprompt';
import { v4 } from 'uuid';
import {
  InternalFlowConfig,
  InternalStreamingFlowConfig,
} from '../../core/lib/flow.js';
import { logger } from './logging.js';
import {
  defineModel,
  DefineModelOptions,
  GenerateResponseChunkData,
  ModelAction,
} from './model.js';
import { lookupAction, Registry, runWithRegistry } from './registry.js';
/**
 * Options for initializing Genkit.
 */
export interface GenkitOptions {
  /** List of plugins to load. */
  plugins?: PluginProvider[];
  /** Directory where dotprompts are stored. */
  promptDir?: string;
  /** Default model to use if no model is specified. */
  model?: ModelArgument<any>;
  // FIXME: This will not actually expose any flows. It needs a new mechanism for exposing endpoints.
  /** Configuration for the flow server. Server will be started if value is true or a configured object. */
  flowServer?: FlowServerOptions | boolean;
}

export interface ExecutablePrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  /**
   * Generates a response by rendering the prompt template with given user input and then calling the model.
   *
   * @param input Prompt inputs.
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  <Out extends O>(
    input?: z.infer<I>,
    opts?: z.infer<CustomOptions>
  ): Promise<GenerateResponse<z.infer<Out>>>;

  /**
   * Generates a streaming response by rendering the prompt template with given user input and then calling the model.
   *
   * @param input Prompt inputs.
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  stream<Out extends O>(
    input?: z.infer<I>,
    opts?: z.infer<CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<Out>>>;

  /**
   * Generates a response by rendering the prompt template with given user input and additional generate options and then calling the model.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateResponse`.
   */
  generate<Out extends O>(
    opt: PromptGenerateOptions<z.infer<I>, CustomOptions>
  ): Promise<GenerateResponse<z.infer<Out>>>;

  /**
   * Generates a streaming response by rendering the prompt template with given user input and additional generate options and then calling the model.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  generateStream<Out extends O>(
    opt: PromptGenerateOptions<z.infer<I>, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<Out>>>;

  /**
   * Renders the prompt template based on user input.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns a `GenerateOptions` object to be used with the `generate()` function from @genkit-ai/ai.
   */
  render<Out extends O>(
    opt: PromptGenerateOptions<z.infer<I>, CustomOptions>
  ): Promise<GenerateOptions<CustomOptions, Out>>;
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
  /** Reflection server for this registry. May be null if not started. */
  private reflectionServer: ReflectionServer | null = null;
  /** Flow server. May be null if the flow server is not enabled in configuration or not started. */
  private flowServer: FlowServer | null = null;
  /** List of flows that have been registered in this instance. */
  private registeredFlows: Flow<any, any, any>[] = [];
  private genkitFunctions: GenkitFunctions;
  private readonly defaultFlowPrefix;
  private flowNameCounter = 0;

  constructor(options?: GenkitOptions) {
    this.options = options || {};
    this.registry = new Registry();
    this.configure();
    this.genkitFunctions = new GenkitFunctions(this.options, this.registry);
    this.defaultFlowPrefix = `default-${v4()}-`;
    if (isDevEnv() && !disableReflectionApi) {
      this.reflectionServer = new ReflectionServer(this.registry, {
        configuredEnvs: [...this.configuredEnvs],
      });
      this.reflectionServer.start().catch((e) => logger.error);
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

  // /**
  //  *
  //  * @param fn Decorator providing the ai functions to the class
  //  */
  // genkit<T extends { new(...args: any[]): {} }>(constructor: T) {
  //   const genkitFunctions = this.genkitFunctions;
  //   return class extends constructor {
  //     ai = genkitFunctions;
  //   }
  // }

  // /**
  //  * Decorator for defining flows
  //  */
  // flow() {
  //   const genkitFunctions = this.genkitFunctions;
  //   const registry = this.registry;
  //   const registeredFlows = this.registeredFlows;
  //   return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
  //     const originalMethod = descriptor.value;
  //     const internalConfig = { primitiveFunctions: genkitFunctions, name: propertyKey };

  //     const flow = runWithRegistry(registry, () => defineFlow(internalConfig, originalMethod));
  //     registeredFlows.push(flow.flow);
  //     descriptor.value = flow;
  //     return descriptor;
  //   }
  // }

  /**
   * Allows direct invocation of genkit functions but will chain all subsequent calls
   * made with this instance in a single trace.
   */
  inFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(fn: FlowFn<GenkitFunctions, I, O>): CallableFlow<GenkitFunctions, I, O>;
  inFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    name: string,
    fn: FlowFn<GenkitFunctions, I, O>
  ): CallableFlow<GenkitFunctions, I, O>;
  inFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    nameOrFn: string | FlowFn<GenkitFunctions, I, O>,
    fn?: FlowFn<GenkitFunctions, I, O>
  ): CallableFlow<GenkitFunctions, I, O> {
    let internalConfig: InternalFlowConfig<GenkitFunctions, I, O>;
    let func: FlowFn<GenkitFunctions, I, O>;

    if (typeof nameOrFn === 'string') {
      internalConfig = {
        primitiveFunctions: this.genkitFunctions,
        name: nameOrFn,
      };
      if (fn === undefined || fn === null) {
        throw new Error('No FlowFn was passed to inFlow');
      } else {
        func = fn;
      }
    } else {
      internalConfig = {
        primitiveFunctions: this.genkitFunctions,
        name: this.defaultFlowPrefix + this.flowNameCounter,
      };
      this.flowNameCounter++;
      func = nameOrFn;
    }
    const flow = runWithRegistry(this.registry, () =>
      defineFlow(internalConfig, func)
    );
    this.registeredFlows.push(flow.flow);
    return flow;
  }

  /**
   * Allows direct invocation of genkit functions but will chain all subsequent calls
   * made with this instance in a single trace.
   */
  defineFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    config: FlowConfig<I, O> | string,
    fn: FlowFn<GenkitFunctions, I, O>
  ): CallableFlow<GenkitFunctions, I, O> {
    let internalConfig: InternalFlowConfig<GenkitFunctions, I, O>;
    if (typeof config === 'string') {
      internalConfig = {
        primitiveFunctions: this.genkitFunctions,
        name: config,
      };
    } else {
      config = config as FlowConfig<I, O>;
      internalConfig = { primitiveFunctions: this.genkitFunctions, ...config };
    }
    const flow = runWithRegistry(this.registry, () =>
      defineFlow(internalConfig, fn)
    );
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
    fn: FlowFn<GenkitFunctions, I, O, S>
  ): StreamableFlow<GenkitFunctions, I, O, S> {
    const internalConfig: InternalStreamingFlowConfig<
      GenkitFunctions,
      I,
      O,
      S
    > = { primitiveFunctions: this.genkitFunctions, ...config };
    const flow = runWithRegistry(this.registry, () =>
      defineStreamingFlow(internalConfig, fn)
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
    return runWithRegistry(this.registry, () => defineSchema(name, schema));
  }

  /**
   * Defines and registers a schema from a JSON schema.
   *
   * Defined schemas can be referenced by `name` in prompts in place of inline schemas.
   */
  defineJsonSchema(name: string, jsonSchema: JSONSchema) {
    return runWithRegistry(this.registry, () =>
      defineJsonSchema(name, jsonSchema)
    );
  }

  /**
   * Defines a new model and adds it to the registry.
   */
  defineModel<CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny>(
    options: DefineModelOptions<CustomOptionsSchema>,
    runner: (
      request: GenerateRequest<CustomOptionsSchema>,
      streamingCallback?: StreamingCallback<GenerateResponseChunkData>
    ) => Promise<GenerateResponseData>
  ): ModelAction<CustomOptionsSchema> {
    return runWithRegistry(this.registry, () => defineModel(options, runner));
  }

  /**
   * Defines and registers a dotprompt.
   *
   * This replaces defining and importing a .dotprompt file.
   *
   * @todo TODO: Improve this documentation (show an example, etc).
   */
  definePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions> & {
      /** The name of the prompt. */
      name: string;
    },
    template: string
  ): ExecutablePrompt<I, O, CustomOptions>;

  definePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions> & {
      /** The name of the prompt. */
      name: string;
    },
    fn: PromptFn<I>
  ): ExecutablePrompt<I, O, CustomOptions>;

  definePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: PromptMetadata<I, CustomOptions> & {
      /** The name of the prompt. */
      name: string;
    },
    templateOrFn: string | PromptFn<I>
  ): ExecutablePrompt<I, O, CustomOptions> {
    if (!options.name) {
      throw new Error('options.name is required');
    }
    return runWithRegistry(this.registry, () => {
      if (!options.name) {
        throw new Error('options.name is required');
      }
      if (typeof templateOrFn === 'string') {
        const dotprompt = defineDotprompt(options, templateOrFn as string);
        return this.wrapDotpromptInExecutablePrompt(dotprompt, options);
      } else {
        const p = definePrompt(
          {
            name: options.name!,
            inputJsonSchema: options.input?.jsonSchema,
            inputSchema: options.input?.schema,
          },
          templateOrFn as PromptFn<I>
        );
        return this.wrapPromptActionInExecutablePrompt(p, options);
      }
    });
  }

  private wrapDotpromptInExecutablePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    dotprompt: Dotprompt<z.infer<I>>,
    options: PromptMetadata<I, CustomOptions>
  ): ExecutablePrompt<I, O, CustomOptions> {
    const executablePrompt = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        return dotprompt.generate({
          model,
          input,
          config: opts,
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).stream = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateStreamResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        return dotprompt.generateStream({
          model,
          input,
          config: opts,
        }) as Promise<GenerateStreamResponse<O>>;
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generate = (
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = !opt.model
          ? await this.resolveModel(options.model)
          : undefined;
        return dotprompt.generate({
          model,
          ...opt,
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generateStream =
      (
        opt: PromptGenerateOptions<I, CustomOptions>
      ): Promise<GenerateStreamResponse<O>> => {
        return runWithRegistry(this.registry, async () => {
          const model = !opt.model
            ? await this.resolveModel(options.model)
            : undefined;
          return dotprompt.generateStream<CustomOptions>({
            model,
            ...opt,
          }) as Promise<GenerateStreamResponse<O>>;
        });
      };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).render = <
      Out extends O,
    >(
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateOptions<CustomOptions, Out>> => {
      return runWithRegistry(
        this.registry,
        async () =>
          dotprompt.render({
            ...opt,
          }) as GenerateOptions<CustomOptions, Out>
      );
    };
    return executablePrompt as ExecutablePrompt<I, O, CustomOptions>;
  }

  private wrapPromptActionInExecutablePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    p: PromptAction<I>,
    options: PromptMetadata<I, CustomOptions>
  ): ExecutablePrompt<I, O, CustomOptions> {
    const executablePrompt = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateResponse> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        const promptResult = await p(input);
        return this.genkitFunctions.generate({
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          config: {
            ...options.config,
            ...opts,
            ...promptResult.config,
          },
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).stream = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateStreamResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        const promptResult = await p(input);
        return this.genkitFunctions.generateStream({
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          config: {
            ...options.config,
            ...promptResult.config,
            ...opts,
          },
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generate = (
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = !opt.model
          ? await this.resolveModel(options.model)
          : undefined;
        const promptResult = await p(opt.input);
        return this.genkitFunctions.generate({
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          ...opt,
          config: {
            ...options.config,
            ...promptResult.config,
            ...opt.config,
          },
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generateStream =
      (
        opt: PromptGenerateOptions<I, CustomOptions>
      ): Promise<GenerateStreamResponse<O>> => {
        return runWithRegistry(this.registry, async () => {
          const model = !opt.model
            ? await this.resolveModel(options.model)
            : undefined;
          const promptResult = await p(opt.input);
          return this.genkitFunctions.generateStream<O, CustomOptions>({
            model,
            messages: promptResult.messages,
            context: promptResult.context,
            tools: promptResult.tools,
            output: {
              format: promptResult.output?.format,
              jsonSchema: promptResult.output?.schema,
            } as any /* FIXME - schema type inference is borken */,
            ...opt,
            config: {
              ...options.config,
              ...promptResult.config,
              ...opt.config,
            },
          });
        });
      };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).render = <
      Out extends O,
    >(
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateOptions<CustomOptions, Out>> => {
      return runWithRegistry(this.registry, async () => {
        const model = !opt.model
          ? await this.resolveModel(options.model)
          : undefined;
        const promptResult = await p(opt.input);
        return {
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          ...opt,
          config: {
            ...options.config,
            ...promptResult.config,
            ...opt.config,
          },
        } as GenerateOptions<CustomOptions, Out>;
      });
    };
    return executablePrompt as ExecutablePrompt<I, O, CustomOptions>;
  }

  /**
   * Configures the Genkit instance.
   */
  private configure() {
    this.options.plugins?.forEach((plugin) => {
      logger.debug(`Registering plugin ${plugin.name}...`);
      const activeRegistry = this.registry;
      activeRegistry.registerPluginProvider(plugin.name, {
        name: plugin.name,
        async initializer() {
          logger.debug(`Initializing plugin ${plugin.name}:`);
          return runWithRegistry(activeRegistry, () => plugin.initializer());
        },
      });
    });
  }

  /**
   * Stops all servers.
   */
  async stopServers() {
    await Promise.all([this.reflectionServer?.stop(), this.flowServer?.stop()]);
    this.reflectionServer = null;
    this.flowServer = null;
  }

  private async resolveModel(
    modelArg: ModelArgument<any> | undefined
  ): Promise<ModelAction> {
    if (!modelArg) {
      if (!this.options.model) {
        throw new Error('Unable to resolve model.');
      }
      return this.resolveModel(this.options.model);
    }
    if (typeof modelArg === 'string') {
      return (await lookupAction(`/model/${modelArg}`)) as ModelAction;
    } else if (modelArg.hasOwnProperty('name')) {
      const ref = modelArg as ModelReference<any>;
      return (await lookupAction(`/model/${ref.name}`)) as ModelAction;
    } else {
      return modelArg as ModelAction;
    }
  }
}

/**
 * Genkit direct functions
 */
class GenkitFunctions {
  /** Registry instance that is exclusively modified by this Genkit instance. */
  readonly registry: Registry;
  /** Developer-configured options. */
  readonly options: GenkitOptions;

  constructor(options: GenkitOptions, registry?: Registry) {
    this.registry = registry || new Registry();
    this.options = options;
  }

  /**
   * Looks up a prompt by `name` and optional `variant`.
   *
   * @todo TODO: Show an example of a name and variant.
   */
  prompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    name: string,
    options?: { variant?: string }
  ): Promise<ExecutablePrompt<I, O, CustomOptions>> {
    return runWithRegistry(this.registry, async () => {
      const action = (await lookupAction(`/prompt/${name}`)) as PromptAction;
      if (
        action.__action?.metadata?.prompt &&
        Object.keys(action.__action.metadata.prompt).length > 0
      ) {
        const p = await prompt(name, options);
        return this.wrapDotpromptInExecutablePrompt(p, {}) as ExecutablePrompt<
          I,
          O,
          CustomOptions
        >;
      } else {
        return this.wrapPromptActionInExecutablePrompt(
          action,
          {}
        ) as ExecutablePrompt<I, O, CustomOptions>;
      }
    });
  }

  /**
   * Embeds the given `content` using the specified `embedder`.
   */
  embed<CustomOptions extends z.ZodTypeAny>(
    params: EmbedderParams<CustomOptions>
  ): Promise<Embedding> {
    // TODO: this doesn't quite work because the default flow requires input/options/output
    // We don't necessarily know or need to know that at this point
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

  private wrapDotpromptInExecutablePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    dotprompt: Dotprompt<z.infer<I>>,
    options: PromptMetadata<I, CustomOptions>
  ): ExecutablePrompt<I, O, CustomOptions> {
    const executablePrompt = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        return dotprompt.generate({
          model,
          input,
          config: opts,
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).stream = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateStreamResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        return dotprompt.generateStream({
          model,
          input,
          config: opts,
        }) as Promise<GenerateStreamResponse<O>>;
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generate = (
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = !opt.model
          ? await this.resolveModel(options.model)
          : undefined;
        return dotprompt.generate({
          model,
          ...opt,
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generateStream =
      (
        opt: PromptGenerateOptions<I, CustomOptions>
      ): Promise<GenerateStreamResponse<O>> => {
        return runWithRegistry(this.registry, async () => {
          const model = !opt.model
            ? await this.resolveModel(options.model)
            : undefined;
          return dotprompt.generateStream<CustomOptions>({
            model,
            ...opt,
          }) as Promise<GenerateStreamResponse<O>>;
        });
      };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).render = <
      Out extends O,
    >(
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateOptions<CustomOptions, Out>> => {
      return runWithRegistry(
        this.registry,
        async () =>
          dotprompt.render({
            ...opt,
          }) as GenerateOptions<CustomOptions, Out>
      );
    };
    return executablePrompt as ExecutablePrompt<I, O, CustomOptions>;
  }

  private wrapPromptActionInExecutablePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    p: PromptAction<I>,
    options: PromptMetadata<I, CustomOptions>
  ): ExecutablePrompt<I, O, CustomOptions> {
    const executablePrompt = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateResponse> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        const promptResult = await p(input);
        return this.generate({
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          config: {
            ...options.config,
            ...opts,
            ...promptResult.config,
          },
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).stream = (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateStreamResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = await this.resolveModel(options.model);
        const promptResult = await p(input);
        return this.generateStream({
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          config: {
            ...options.config,
            ...promptResult.config,
            ...opts,
          },
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generate = (
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateResponse<O>> => {
      return runWithRegistry(this.registry, async () => {
        const model = !opt.model
          ? await this.resolveModel(options.model)
          : undefined;
        const promptResult = await p(opt.input);
        return this.generate({
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          ...opt,
          config: {
            ...options.config,
            ...promptResult.config,
            ...opt.config,
          },
        });
      });
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).generateStream =
      (
        opt: PromptGenerateOptions<I, CustomOptions>
      ): Promise<GenerateStreamResponse<O>> => {
        return runWithRegistry(this.registry, async () => {
          const model = !opt.model
            ? await this.resolveModel(options.model)
            : undefined;
          const promptResult = await p(opt.input);
          return this.generateStream<O, CustomOptions>({
            model,
            messages: promptResult.messages,
            context: promptResult.context,
            tools: promptResult.tools,
            output: {
              format: promptResult.output?.format,
              jsonSchema: promptResult.output?.schema,
            } as any /* FIXME - schema type inference is borken */,
            ...opt,
            config: {
              ...options.config,
              ...promptResult.config,
              ...opt.config,
            },
          });
        });
      };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).render = <
      Out extends O,
    >(
      opt: PromptGenerateOptions<I, CustomOptions>
    ): Promise<GenerateOptions<CustomOptions, Out>> => {
      return runWithRegistry(this.registry, async () => {
        const model = !opt.model
          ? await this.resolveModel(options.model)
          : undefined;
        const promptResult = await p(opt.input);
        return {
          model,
          messages: promptResult.messages,
          context: promptResult.context,
          tools: promptResult.tools,
          output: {
            format: promptResult.output?.format,
            jsonSchema: promptResult.output?.schema,
          },
          ...opt,
          config: {
            ...options.config,
            ...promptResult.config,
            ...opt.config,
          },
        } as GenerateOptions<CustomOptions, Out>;
      });
    };
    return executablePrompt as ExecutablePrompt<I, O, CustomOptions>;
  }

  private async resolveModel(
    modelArg: ModelArgument<any> | undefined
  ): Promise<ModelAction> {
    if (!modelArg) {
      if (!this.options.model) {
        throw new Error('Unable to resolve model.');
      }
      return this.resolveModel(this.options.model);
    }
    if (typeof modelArg === 'string') {
      return (await lookupAction(`/model/${modelArg}`)) as ModelAction;
    } else if (modelArg.hasOwnProperty('name')) {
      const ref = modelArg as ModelReference<any>;
      return (await lookupAction(`/model/${ref.name}`)) as ModelAction;
    } else {
      return modelArg as ModelAction;
    }
  }
}

/**
 * Initializes Genkit with a set of options.
 *
 * This will create a new Genkit registry, register the provided plugins, stores, and other configuration. This
 * should be called before any flows are registered.
 */
export function genkit(options: GenkitOptions): Genkit {
  return new Genkit(options);
}

process.on('SIGTERM', async () => {
  logger.debug('Received SIGTERM. Shutting down all Genkit servers...');
  await Promise.all([ReflectionServer.stopAll(), FlowServer.stopAll()]);
  process.exit(0);
});

let disableReflectionApi = false;

export function __disableReflectionApi() {
  disableReflectionApi = true;
}

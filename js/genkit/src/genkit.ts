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
  Part,
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
import { v4 as uuidv4 } from 'uuid';
import { Chat, ChatOptions, MAIN_THREAD } from './chat.js';
import { logger } from './logging.js';
import {
  defineModel,
  DefineModelOptions,
  GenerateResponseChunkData,
  ModelAction,
} from './model.js';
import { lookupAction, Registry, runWithRegistry } from './registry.js';
import {
  getCurrentSession,
  Session,
  SessionData,
  SessionError,
  SessionOptions,
} from './session.js';

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
   * Generates a response by rendering the prompt template with given user input and then calling the model.
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

  constructor(options?: GenkitOptions) {
    this.options = options || {};
    this.registry = new Registry();
    this.configure();
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

  /**
   * Defines and registers a non-streaming flow.
   *
   * @todo TODO: Improve this documentation (show snippets, etc).
   */
  defineFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
  >(config: FlowConfig<I, O> | string, fn: FlowFn<I, O>): CallableFlow<I, O> {
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
   * Defines and registers a dotprompt.
   *
   * This is an alternative to defining and importing a .prompt file.
   *
   * ```ts
   * const hi = ai.definePrompt(
   *   {
   *     name: 'hi',
   *     input: {
   *       schema: z.object({
   *         name: z.string(),
   *       }),
   *     },
   *   },
   *   'hi {{ name }}'
   * );
   * const { text } = await hi({ name: 'Genkit' });
   * ```
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

  /**
   * Defines and registers a function-based prompt.
   *
   * ```ts
   * const hi = ai.definePrompt(
   *   {
   *     name: 'hi',
   *     input: {
   *       schema: z.object({
   *         name: z.string(),
   *       }),
   *     },
   *     config: {
   *       temperature: 1,
   *     },
   *   },
   *   async (input) => {
   *     return {
   *       messages: [ { role: 'user', content: [{ text: `hi ${input.name}` }] } ],
   *     };
   *   }
   * );
   * const { text } = await hi({ name: 'Genkit' });
   * ```
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
        return this.generate({
          model,
          messages: promptResult.messages,
          docs: promptResult.docs,
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
          docs: promptResult.docs,
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
          docs: promptResult.docs,
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
            docs: promptResult.docs,
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
          docs: promptResult.docs,
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
   * Make a generate call to the default model with a simple text prompt.
   *
   * ```ts
   * const ai = genkit({
   *   plugins: [googleAI()],
   *   model: gemini15Flash, // default model
   * })
   *
   * const { text } = await ai.generate('hi');
   * ```
   */
  generate<O extends z.ZodTypeAny = z.ZodTypeAny>(
    strPrompt: string
  ): Promise<GenerateResponse<z.infer<O>>>;

  /**
   * Make a generate call to the default model with a multipart request.
   *
   * ```ts
   * const ai = genkit({
   *   plugins: [googleAI()],
   *   model: gemini15Flash, // default model
   * })
   *
   * const { text } = await ai.generate([
   *   { media: {url: 'http://....'} },
   *   { text: 'describe this image' }
   * ]);
   * ```
   */
  generate<O extends z.ZodTypeAny = z.ZodTypeAny>(
    parts: Part[]
  ): Promise<GenerateResponse<z.infer<O>>>;

  /**
   * Generate calls a generative model based on the provided prompt and configuration. If
   * `messages` is provided, the generation will include a conversation history in its
   * request. If `tools` are provided, the generate method will automatically resolve
   * tool calls returned from the model unless `returnToolRequests` is set to `true`.
   *
   * See {@link GenerateOptions} for detailed information about available options.
   *
   * ```ts
   * const ai = genkit({
   *   plugins: [googleAI()],
   * })
   *
   * const { text } = await ai.generate({
   *   system: 'talk like a pirate',
   *   prompt: [
   *     { media: { url: 'http://....' } },
   *     { text: 'describe this image' }
   *   ],
   *   messages: conversationHistory,
   *   tools: [ userInfoLookup ],
   *   model: gemini15Flash,
   * });
   * ```
   */
  generate<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    parts:
      | GenerateOptions<O, CustomOptions>
      | PromiseLike<GenerateOptions<O, CustomOptions>>
  ): Promise<GenerateResponse<z.infer<O>>>;

  async generate<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options:
      | string
      | Part[]
      | GenerateOptions<O, CustomOptions>
      | PromiseLike<GenerateOptions<O, CustomOptions>>
  ): Promise<GenerateResponse<z.infer<O>>> {
    let resolvedOptions: GenerateOptions<O, CustomOptions>;
    if (options instanceof Promise) {
      resolvedOptions = await options;
    } else if (typeof options === 'string' || Array.isArray(options)) {
      resolvedOptions = {
        prompt: options,
      };
    } else {
      resolvedOptions = options as GenerateOptions<O, CustomOptions>;
    }
    if (!resolvedOptions.model) {
      resolvedOptions.model = this.options.model;
    }
    return runWithRegistry(this.registry, () => generate(resolvedOptions));
  }

  /**
   * Make a streaming generate call to the default model with a simple text prompt.
   *
   * ```ts
   * const ai = genkit({
   *   plugins: [googleAI()],
   *   model: gemini15Flash, // default model
   * })
   *
   * const { response, stream } = await ai.generateStream('hi');
   * for await (const chunk of stream) {
   *   console.log(chunk.text);
   * }
   * console.log((await response).text);
   * ```
   */
  generateStream<O extends z.ZodTypeAny = z.ZodTypeAny>(
    strPrompt: string
  ): Promise<GenerateStreamResponse<z.infer<O>>>;

  /**
   * Make a streaming generate call to the default model with a multipart request.
   *
   * ```ts
   * const ai = genkit({
   *   plugins: [googleAI()],
   *   model: gemini15Flash, // default model
   * })
   *
   * const { response, stream } = await ai.generateStream([
   *   { media: {url: 'http://....'} },
   *   { text: 'describe this image' }
   * ]);
   * for await (const chunk of stream) {
   *   console.log(chunk.text);
   * }
   * console.log((await response).text);
   * ```
   */
  generateStream<O extends z.ZodTypeAny = z.ZodTypeAny>(
    parts: Part[]
  ): Promise<GenerateStreamResponse<z.infer<O>>>;

  /**
   * Streaming generate calls a generative model based on the provided prompt and configuration. If
   * `messages` is provided, the generation will include a conversation history in its
   * request. If `tools` are provided, the generate method will automatically resolve
   * tool calls returned from the model unless `returnToolRequests` is set to `true`.
   *
   * See {@link GenerateOptions} for detailed information about available options.
   *
   * ```ts
   * const ai = genkit({
   *   plugins: [googleAI()],
   * })
   *
   * const { response, stream } = await ai.generateStream({
   *   system: 'talk like a pirate',
   *   prompt: [
   *     { media: { url: 'http://....' } },
   *     { text: 'describe this image' }
   *   ],
   *   messages: conversationHistory,
   *   tools: [ userInfoLookup ],
   *   model: gemini15Flash,
   * });
   * for await (const chunk of stream) {
   *   console.log(chunk.text);
   * }
   * console.log((await response).text);
   * ```
   */
  generateStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    parts:
      | GenerateOptions<O, CustomOptions>
      | PromiseLike<GenerateOptions<O, CustomOptions>>
  ): Promise<GenerateStreamResponse<z.infer<O>>>;

  async generateStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options:
      | string
      | Part[]
      | GenerateStreamOptions<O, CustomOptions>
      | PromiseLike<GenerateStreamOptions<O, CustomOptions>>
  ): Promise<GenerateStreamResponse<z.infer<O>>> {
    let resolvedOptions: GenerateOptions<O, CustomOptions>;
    if (options instanceof Promise) {
      resolvedOptions = await options;
    } else if (typeof options === 'string' || Array.isArray(options)) {
      resolvedOptions = {
        prompt: options,
      };
    } else {
      resolvedOptions = options as GenerateOptions<O, CustomOptions>;
    }
    if (!resolvedOptions.model) {
      resolvedOptions.model = this.options.model;
    }
    return runWithRegistry(this.registry, () =>
      generateStream(resolvedOptions)
    );
  }

  /**
   * Create a chat session with the provided options.
   *
   * ```ts
   * const chat = ai.chat({
   *   system: 'talk like a pirate',
   * })
   * let response = await chat.send('tell me a joke')
   * response = await chat.send('another one')
   * ```
   */
  chat(options?: ChatOptions): Promise<Chat> {
    this.createSession();
    return new Chat(
      this,
      {
        ...options,
      },
      {
        store: options?.store,
      }
    );
  }

  /**
   * Load a chat session from the provided store.
   */
  async loadChat(sessionId: string, options: ChatOptions): Promise<Chat> {
    if (!options.store) {
      throw new Error('options.store is required for loading chat sessions');
    }
    const sessionData = await options.store.get(sessionId);
    if (!sessionData) {
      throw new Error(`chat session ${sessionId} not found`);
    }
    return new Chat(
      this,
      {
        ...options,
      },
      {
        id: sessionId,
        sessionData,
        stateSchema: options?.stateSchema,
        store: options?.store,
      }
    );
  }

  /**
   * Create a session for this environment.
   */
  async createSession(options?: SessionOptions): Promise<Session> {
    const sessionId = uuidv4();
    const sessionData: SessionData = {
      state: options?.state,
      threads: {
        [MAIN_THREAD]: options?.messages ?? [],
      },
    };
    if (options?.store) {
      await options.store.save(sessionId, sessionData);
    }
    return new Session(
      this,
      {
        ...options,
      },
      {
        id: sessionId,
        sessionData,
        stateSchema: options?.stateSchema,
        store: options?.store,
      }
    );
  }

  /**
   * Loads a session from the store.
   */
  async loadSession(
    sessionId: string,
    options: SessionOptions
  ): Promise<Session> {
    if (!options.store) {
      throw new Error('options.store is required');
    }
    const sessionData = await options.store.get(sessionId);

    return new Session(
      this,
      {
        ...options,
      },
      {
        id: sessionId,
        sessionData,
        stateSchema: options?.stateSchema,
        store: options.store,
      }
    );
  }

  /**
   * Gets the current session from async local storage.
   */
  get currentSession(): Session {
    const currentSession = getCurrentSession();
    if (!currentSession) {
      throw new SessionError('not running within a session');
    }
    return currentSession as Session;
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
 * Initializes Genkit with a set of options.
 *
 * This will create a new Genkit registry, register the provided plugins, stores, and other configuration. This
 * should be called before any flows are registered.
 */
export function genkit(options: GenkitOptions): Genkit {
  return new Genkit(options);
}

const shutdown = async () => {
  logger.info('Shutting down all Genkit servers...');
  await Promise.all([ReflectionServer.stopAll(), FlowServer.stopAll()]);
  process.exit(0);
};

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

let disableReflectionApi = false;

export function __disableReflectionApi() {
  disableReflectionApi = true;
}

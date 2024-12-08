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
  EmbedderInfo,
  EmbedderParams,
  Embedding,
  EvalResponses,
  evaluate,
  EvaluatorParams,
  ExecutablePrompt,
  generate,
  GenerateOptions,
  GenerateRequest,
  GenerateResponse,
  GenerateResponseData,
  generateStream,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  IndexerParams,
  isExecutablePrompt,
  ModelArgument,
  ModelReference,
  Part,
  PromptAction,
  PromptFn,
  PromptGenerateOptions,
  RankedDocument,
  rerank,
  RerankerParams,
  retrieve,
  RetrieverAction,
  RetrieverInfo,
  RetrieverParams,
  ToolAction,
  ToolConfig,
} from '@genkit-ai/ai';
import { Chat, ChatOptions } from '@genkit-ai/ai/chat';
import {
  defineEmbedder,
  EmbedderAction,
  EmbedderArgument,
  EmbedderFn,
  EmbeddingBatch,
  embedMany,
} from '@genkit-ai/ai/embedder';
import {
  defineEvaluator,
  EvaluatorAction,
  EvaluatorFn,
} from '@genkit-ai/ai/evaluator';
import {
  configureFormats,
  defineFormat,
  Formatter,
} from '@genkit-ai/ai/formats';
import {
  defineModel,
  DefineModelOptions,
  GenerateResponseChunkData,
  ModelAction,
} from '@genkit-ai/ai/model';
import {
  defineReranker,
  RerankerFn,
  RerankerInfo,
} from '@genkit-ai/ai/reranker';
import {
  defineIndexer,
  defineRetriever,
  defineSimpleRetriever,
  DocumentData,
  index,
  IndexerAction,
  IndexerFn,
  RetrieverFn,
  SimpleRetrieverOptions,
} from '@genkit-ai/ai/retriever';
import {
  getCurrentSession,
  Session,
  SessionData,
  SessionError,
  SessionOptions,
} from '@genkit-ai/ai/session';
import { resolveTools } from '@genkit-ai/ai/tool';
import {
  CallableFlow,
  defineFlow,
  defineJsonSchema,
  defineSchema,
  defineStreamingFlow,
  Flow,
  FlowFn,
  FlowServer,
  FlowServerOptions,
  isDevEnv,
  JSONSchema,
  ReflectionServer,
  StreamableFlow,
  StreamingCallback,
  StreamingFlowConfig,
  z,
} from '@genkit-ai/core';
import {
  defineDotprompt,
  defineHelper,
  definePartial,
  Dotprompt,
  PromptMetadata as DotpromptPromptMetadata,
  loadPromptFolder,
  prompt,
} from '@genkit-ai/dotprompt';
import { v4 as uuidv4 } from 'uuid';
import { BaseEvalDataPointSchema } from './evaluator.js';
import { logger } from './logging.js';
import { GenkitPlugin, genkitPlugin } from './plugin.js';
import { Registry } from './registry.js';
import { toJsonSchema } from './schema.js';
import { toToolDefinition } from './tool.js';

/**
 * Options for initializing Genkit.
 */
export interface GenkitOptions {
  /** List of plugins to load. */
  plugins?: GenkitPlugin[];
  /** Directory where dotprompts are stored. */
  promptDir?: string;
  /** Default model to use if no model is specified. */
  model?: ModelArgument<any>;
}

/**
 * Metadata for a prompt.
 */
export type PromptMetadata<
  Input extends z.ZodTypeAny = z.ZodTypeAny,
  Options extends z.ZodTypeAny = z.ZodTypeAny,
> = Omit<DotpromptPromptMetadata<Input, Options>, 'name'> & {
  /** The name of the prompt. */
  name: string;
};

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
  }

  /**
   * Defines and registers a non-streaming flow.
   *
   * @todo TODO: Improve this documentation (show snippets, etc).
   */
  defineFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    S extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    config: StreamingFlowConfig<I, O, S> | string,
    fn: FlowFn<I, O, S>
  ): CallableFlow<I, O, S> {
    const flow = defineFlow(this.registry, config, fn);
    this.registeredFlows.push(flow.flow);
    return flow;
  }

  /**
   * Defines and registers a streaming flow.
   *
   * @deprecated use {@link defineFlow}
   */
  defineStreamingFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    S extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    config: StreamingFlowConfig<I, O, S> | string,
    fn: FlowFn<I, O, S>
  ): StreamableFlow<I, O, S> {
    const flow = defineStreamingFlow(
      this.registry,
      typeof config === 'string' ? { name: config } : config,
      fn
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
    return defineTool(this.registry, config, fn);
  }

  /**
   * Defines and registers a schema from a Zod schema.
   *
   * Defined schemas can be referenced by `name` in prompts in place of inline schemas.
   */
  defineSchema<T extends z.ZodTypeAny>(name: string, schema: T): T {
    return defineSchema(this.registry, name, schema);
  }

  /**
   * Defines and registers a custom model output formatter.
   *
   * Here's an example of a custom JSON output formatter:
   *
   * ```ts
   * import { extractJson } from 'genkit/extract';
   *
   * ai.defineFormat(
   *   { name: 'customJson' },
   *   (schema) => {
   *     let instructions: string | undefined;
   *     if (schema) {
   *       instructions = `Output should be in JSON format and conform to the following schema:
   * \`\`\`
   * ${JSON.stringify(schema)}
   * \`\`\`
   * `;
   *     }
   *     return {
   *       parseChunk: (chunk) => extractJson(chunk.accumulatedText),
   *       parseMessage: (message) => extractJson(message.text),
   *       instructions,
   *     };
   *   }
   * );
   *
   * const { output } = await ai.generate({
   *   prompt: 'Invent a menu item for a pirate themed restaurant.',
   *   output: { format: 'customJson', schema: MenuItemSchema },
   * });
   * ```
   */
  defineFormat(
    options: {
      name: string;
    } & Formatter['config'],
    handler: Formatter['handler']
  ): { config: Formatter['config']; handler: Formatter['handler'] } {
    return defineFormat(this.registry, options, handler);
  }

  /**
   * Defines and registers a schema from a JSON schema.
   *
   * Defined schemas can be referenced by `name` in prompts in place of inline schemas.
   */
  defineJsonSchema(name: string, jsonSchema: JSONSchema) {
    return defineJsonSchema(this.registry, name, jsonSchema);
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
    return defineModel(this.registry, options, runner);
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
  ): ExecutablePrompt<z.infer<I>, O, CustomOptions> {
    const actionPromise = (async () => {
      // check the registry first as not all prompt types can be
      // loaded by dotprompt (e.g. functional)
      let action = (await this.registry.lookupAction(
        `/prompt/${name}${options?.variant ? `.${options?.variant}` : ''}`
      )) as PromptAction<I>;
      // nothing in registry - check for dotprompt file.
      if (!action) {
        action = (
          await prompt(this.registry, name, {
            ...options,
            dir: this.options.promptDir ?? './prompts',
          })
        ).promptAction as PromptAction<I>;
      }
      const { template, ...opts } = action.__action.metadata!.prompt;
      return { action, opts };
    })();

    // make sure we get configuration such as model name if applicable
    return this.wrapPromptActionInExecutablePrompt(
      actionPromise.then(({ action }) => action),
      actionPromise.then(({ opts }) => opts)
    ) as ExecutablePrompt<I, O, CustomOptions>;
  }

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
    options: PromptMetadata<I, CustomOptions>,
    fn: PromptFn<I>
  ): ExecutablePrompt<z.infer<I>, O, CustomOptions>;

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
    options: PromptMetadata<I, CustomOptions>,
    template: string
  ): ExecutablePrompt<z.infer<I>, O, CustomOptions>;

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
  ): ExecutablePrompt<z.infer<I>, O, CustomOptions> {
    if (!options.name) {
      throw new Error('options.name is required');
    }
    if (!options.name) {
      throw new Error('options.name is required');
    }
    if (typeof templateOrFn === 'string') {
      const dotprompt = defineDotprompt(
        this.registry,
        {
          ...options,
          tools: options.tools,
        },
        templateOrFn as string
      );
      return this.wrapPromptActionInExecutablePrompt(
        dotprompt.promptAction! as PromptAction<I>,
        options,
        dotprompt
      );
    } else {
      const p = definePrompt(
        this.registry,
        {
          name: options.name!,
          inputJsonSchema: options.input?.jsonSchema,
          inputSchema: options.input?.schema,
          description: options.description,
        },
        async (input: z.infer<I>) => {
          const response = await (templateOrFn as PromptFn<I>)(input);
          if (!response.tools && options.tools) {
            response.tools = (
              await resolveTools(this.registry, options.tools)
            ).map((t) => toToolDefinition(t));
          }
          if (!response.output && options.output) {
            response.output = {
              schema: toJsonSchema({
                schema: options.output.schema,
                jsonSchema: options.output.jsonSchema,
              }),
            };
          }
          return response;
        }
      );
      return this.wrapPromptActionInExecutablePrompt(p, options);
    }
  }

  private wrapPromptActionInExecutablePrompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    promptAction: PromptAction<I> | Promise<PromptAction<I>>,
    options:
      | Partial<PromptMetadata<I, CustomOptions>>
      | Promise<Partial<PromptMetadata<I, CustomOptions>>>,
    dotprompt?: Dotprompt<z.infer<I>>
  ): ExecutablePrompt<I, O, CustomOptions> {
    const executablePrompt = async (
      input?: z.infer<I>,
      opts?: PromptGenerateOptions<O, CustomOptions>
    ): Promise<GenerateResponse> => {
      const renderedOpts = await (
        executablePrompt as ExecutablePrompt<I, O, CustomOptions>
      ).render({
        ...opts,
        input,
      });
      return this.generate(renderedOpts);
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).stream = async (
      input?: z.infer<I>,
      opts?: z.infer<CustomOptions>
    ): Promise<GenerateStreamResponse<O>> => {
      const renderedOpts = await (
        executablePrompt as ExecutablePrompt<I, O, CustomOptions>
      ).render({
        ...opts,
        input,
      });
      return this.generateStream(renderedOpts);
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).render = async (
      opt: PromptGenerateOptions<O, CustomOptions> & {
        input?: I;
      }
    ): Promise<GenerateOptions<O, CustomOptions>> => {
      let model: ModelAction | undefined;
      options = await options;
      const modelArg = opt?.model ?? options.model;
      if (modelArg) {
        model = await this.resolveModel(modelArg);
        // If model was explicitly specified and we failed to resolve it (bad ref maybe?), throw an error!
        if (!model) {
          throw new Error(`Model ${modelArg} not found`);
        }
      }
      const p = await promptAction;
      // If it's a dotprompt template, we invoke dotprompt template directly
      // because it can take in more PromptGenerateOptions (not just inputs).
      const promptResult = await (dotprompt
        ? dotprompt.render(opt)
        : p(opt.input));
      const resultOptions = {
        messages: promptResult.messages,
        docs: promptResult.docs,
        tools: promptResult.tools ?? options.tools,
        output:
          promptResult.output?.format || promptResult.output?.schema
            ? {
                format: promptResult.output?.format,
                jsonSchema: dotprompt
                  ? (promptResult as GenerateOptions).output?.jsonSchema
                  : promptResult.output.schema,
                contentType: promptResult.output?.contentType,
                instructions: promptResult.output?.instructions,
                schema: promptResult.output?.schema,
              }
            : options.output,
        config: {
          ...options.config,
          ...promptResult.config,
          ...opt.config,
        },
        model,
      } as GenerateOptions<O, CustomOptions>;
      delete (resultOptions as any).input;
      if ((promptResult as GenerateOptions).prompt) {
        resultOptions.prompt = (promptResult as GenerateOptions).prompt;
      }
      return resultOptions;
    };
    (executablePrompt as ExecutablePrompt<I, O, CustomOptions>).asTool =
      async (): Promise<ToolAction<I, O>> => {
        return (await promptAction) as unknown as ToolAction<I, O>;
      };
    return executablePrompt as ExecutablePrompt<I, O, CustomOptions>;
  }

  /**
   * Creates a retriever action for the provided {@link RetrieverFn} implementation.
   */
  defineRetriever<OptionsType extends z.ZodTypeAny = z.ZodTypeAny>(
    options: {
      name: string;
      configSchema?: OptionsType;
      info?: RetrieverInfo;
    },
    runner: RetrieverFn<OptionsType>
  ): RetrieverAction<OptionsType> {
    return defineRetriever(this.registry, options, runner);
  }

  /**
   * defineSimpleRetriever makes it easy to map existing data into documents that
   * can be used for prompt augmentation.
   *
   * @param options Configuration options for the retriever.
   * @param handler A function that queries a datastore and returns items from which to extract documents.
   * @returns A Genkit retriever.
   */
  defineSimpleRetriever<C extends z.ZodTypeAny = z.ZodTypeAny, R = any>(
    options: SimpleRetrieverOptions<C, R>,
    handler: (query: Document, config: z.infer<C>) => Promise<R[]>
  ): RetrieverAction<C> {
    return defineSimpleRetriever(this.registry, options, handler);
  }

  /**
   * Creates an indexer action for the provided {@link IndexerFn} implementation.
   */
  defineIndexer<IndexerOptions extends z.ZodTypeAny>(
    options: {
      name: string;
      embedderInfo?: EmbedderInfo;
      configSchema?: IndexerOptions;
    },
    runner: IndexerFn<IndexerOptions>
  ): IndexerAction<IndexerOptions> {
    return defineIndexer(this.registry, options, runner);
  }

  /**
   * Creates evaluator action for the provided {@link EvaluatorFn} implementation.
   */
  defineEvaluator<
    DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
    EvalDataPoint extends
      typeof BaseEvalDataPointSchema = typeof BaseEvalDataPointSchema,
    EvaluatorOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    options: {
      name: string;
      displayName: string;
      definition: string;
      dataPointType?: DataPoint;
      configSchema?: EvaluatorOptions;
      isBilled?: boolean;
    },
    runner: EvaluatorFn<EvalDataPoint, EvaluatorOptions>
  ): EvaluatorAction {
    return defineEvaluator(this.registry, options, runner);
  }

  /**
   * Creates embedder model for the provided {@link EmbedderFn} model implementation.
   */
  defineEmbedder<ConfigSchema extends z.ZodTypeAny = z.ZodTypeAny>(
    options: {
      name: string;
      configSchema?: ConfigSchema;
      info?: EmbedderInfo;
    },
    runner: EmbedderFn<ConfigSchema>
  ): EmbedderAction<ConfigSchema> {
    return defineEmbedder(this.registry, options, runner);
  }

  /**
   * create a handlebards helper (https://handlebarsjs.com/guide/block-helpers.html) to be used in dotpormpt templates.
   */
  defineHelper(name: string, fn: Handlebars.HelperDelegate) {
    return defineHelper(name, fn);
  }

  /**
   * Creates a handlebars partial (https://handlebarsjs.com/guide/partials.html) to be used in dotpormpt templates.
   */
  definePartial(name: string, source: string) {
    return definePartial(name, source);
  }

  /**
   *  Creates a reranker action for the provided {@link RerankerFn} implementation.
   */
  defineReranker<OptionsType extends z.ZodTypeAny = z.ZodTypeAny>(
    options: {
      name: string;
      configSchema?: OptionsType;
      info?: RerankerInfo;
    },
    runner: RerankerFn<OptionsType>
  ) {
    return defineReranker(this.registry, options, runner);
  }

  /**
   * Embeds the given `content` using the specified `embedder`.
   */
  embed<CustomOptions extends z.ZodTypeAny>(
    params: EmbedderParams<CustomOptions>
  ): Promise<Embedding> {
    return embed(this.registry, params);
  }

  /**
   * A veneer for interacting with embedder models in bulk.
   */
  embedMany<ConfigSchema extends z.ZodTypeAny = z.ZodTypeAny>(params: {
    embedder: EmbedderArgument<ConfigSchema>;
    content: string[] | DocumentData[];
    metadata?: Record<string, unknown>;
    options?: z.infer<ConfigSchema>;
  }): Promise<EmbeddingBatch> {
    return embedMany(this.registry, params);
  }

  /**
   * Evaluates the given `dataset` using the specified `evaluator`.
   */
  evaluate<
    DataPoint extends typeof BaseDataPointSchema = typeof BaseDataPointSchema,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(params: EvaluatorParams<DataPoint, CustomOptions>): Promise<EvalResponses> {
    return evaluate(this.registry, params);
  }

  /**
   * Reranks documents from a {@link RerankerArgument} based on the provided query.
   */
  rerank<CustomOptions extends z.ZodTypeAny>(
    params: RerankerParams<CustomOptions>
  ): Promise<Array<RankedDocument>> {
    return rerank(this.registry, params);
  }

  /**
   * Indexes `documents` using the provided `indexer`.
   */
  index<CustomOptions extends z.ZodTypeAny>(
    params: IndexerParams<CustomOptions>
  ): Promise<void> {
    return index(this.registry, params);
  }

  /**
   * Retrieves documents from the `retriever` based on the provided `query`.
   */
  retrieve<CustomOptions extends z.ZodTypeAny>(
    params: RetrieverParams<CustomOptions>
  ): Promise<Array<Document>> {
    return retrieve(this.registry, params);
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
    opts:
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
    return generate(this.registry, resolvedOptions);
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
    return generateStream(this.registry, resolvedOptions);
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
  chat<I>(options?: ChatOptions<I>): Chat;

  /**
   * Create a chat session with the provided preabmle.
   *
   * ```ts
   * const triageAgent = ai.definePrompt({
   *   system: 'help the user triage a problem',
   * })
   * const chat = ai.chat(triageAgent)
   * const { text } = await chat.send('my phone feels hot');
   * ```
   */
  chat<I>(preamble: ExecutablePrompt<I>, options?: ChatOptions<I>): Chat;

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
  chat<I>(
    preambleOrOptions?: ChatOptions<I> | ExecutablePrompt<I>,
    maybeOptions?: ChatOptions<I>
  ): Chat {
    let options: ChatOptions<I> | undefined;
    let preamble: ExecutablePrompt<I> | undefined;
    if (maybeOptions) {
      options = maybeOptions;
    }
    if (preambleOrOptions) {
      if (isExecutablePrompt(preambleOrOptions)) {
        preamble = preambleOrOptions as ExecutablePrompt<I>;
      } else {
        options = preambleOrOptions as ChatOptions<I>;
      }
    }

    const session = this.createSession();
    if (preamble) {
      return session.chat(preamble, options);
    }
    return session.chat(options);
  }

  /**
   * Create a session for this environment.
   */
  createSession<S = any>(options?: SessionOptions<S>): Session<S> {
    const sessionId = uuidv4();
    const sessionData: SessionData = {
      id: sessionId,
      state: options?.initialState,
    };
    return new Session(this.registry, {
      id: sessionId,
      sessionData,
      store: options?.store,
    });
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

    return new Session(this.registry, {
      id: sessionId,
      sessionData,
      store: options.store,
    });
  }

  /**
   * Gets the current session from async local storage.
   */
  currentSession<S = any>(): Session<S> {
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
    const activeRegistry = this.registry;
    // install the default formats in the registry
    configureFormats(activeRegistry);
    const plugins = [...(this.options.plugins ?? [])];
    if (this.options.model) {
      this.registry.registerValue(
        'defaultModel',
        'defaultModel',
        this.options.model
      );
    }
    if (this.options.promptDir !== null) {
      const dotprompt = genkitPlugin('dotprompt', async (ai) => {
        loadPromptFolder(
          this.registry,
          this.options.promptDir ?? './prompts',
          ''
        );
      });
      plugins.push(dotprompt);
    }
    plugins.forEach((plugin) => {
      const loadedPlugin = plugin(this);
      logger.debug(`Registering plugin ${loadedPlugin.name}...`);
      activeRegistry.registerPluginProvider(loadedPlugin.name, {
        name: loadedPlugin.name,
        async initializer() {
          logger.debug(`Initializing plugin ${loadedPlugin.name}:`);
          await loadedPlugin.initializer();
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
      return (await this.registry.lookupAction(
        `/model/${modelArg}`
      )) as ModelAction;
    } else if ((modelArg as ModelAction).__action) {
      return modelArg as ModelAction;
    } else {
      const ref = modelArg as ModelReference<any>;
      return (await this.registry.lookupAction(
        `/model/${ref.name}`
      )) as ModelAction;
    }
  }

  startFlowServer(options: FlowServerOptions): FlowServer {
    const flowServer = new FlowServer(this.registry, options);
    flowServer.start();
    return flowServer;
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

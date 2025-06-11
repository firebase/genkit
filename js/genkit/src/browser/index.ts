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
  defineHelper,
  definePartial,
  definePrompt,
  defineTool,
  generate,
  generateStream,
  type ExecutablePrompt,
  type GenerateOptions,
  type GenerateRequest,
  type GenerateResponse,
  type GenerateResponseData,
  type GenerateStreamOptions,
  type GenerateStreamResponse,
  type GenerationCommonConfigSchema,
  type ModelArgument,
  type Part,
  type PromptConfig,
  type ToolAction,
  type ToolConfig,
} from '@genkit-ai/ai';
import { configureFormats } from '@genkit-ai/ai/formats';
import {
  defineGenerateAction,
  defineModel,
  type DefineModelOptions,
  type GenerateResponseChunkData,
  type ModelAction,
} from '@genkit-ai/ai/model';
import { dynamicTool, type ToolFn } from '@genkit-ai/ai/tool';
import {
  GenkitError,
  _setPerformanceNowFn,
  defineFlow,
  defineJsonSchema,
  defineSchema,
  getContext,
  run,
  type Action,
  type ActionContext,
  type FlowConfig,
  type FlowFn,
  type JSONSchema,
  type StreamingCallback,
  type z,
} from '@genkit-ai/core';
import type { HasRegistry } from '@genkit-ai/core/registry';
import { type PromptFn } from '../genkit.js';
import { logger } from '../logging.js';
import type { GenkitPlugin } from '../plugin.js';
import { Registry, type ActionType } from '../registry.js';
import { BrowserRegistry } from './registry.js';

_setPerformanceNowFn(() => window.performance.now());

/**
 * Options for initializing Genkit.
 */
export interface GenkitOptions {
  /** List of plugins to load. */
  plugins?: GenkitPlugin[];
  /** Default model to use if no model is specified. */
  model?: ModelArgument<any>;
  /** Additional runtime context data for flows and tools. */
  context?: ActionContext;
}

/**
 * `Genkit` encapsulates a single Genkit instance including the {@link Registry}, {@link ReflectionServer}, {@link FlowServer}, and configuration.
 *
 * Do not instantiate this class directly. Use {@link genkit}.
 *
 * Registry keeps track of actions, flows, tools, and many other components. Reflection server exposes an API to inspect the registry and trigger executions of actions in the registry. Flow server exposes flows as HTTP endpoints for production use.
 *
 * There may be multiple Genkit instances in a single codebase.
 */
export class Genkit implements HasRegistry {
  /** Developer-configured options. */
  readonly options: GenkitOptions;
  /** Registry instance that is exclusively modified by this Genkit instance. */
  readonly registry: Registry;
  /** List of flows that have been registered in this instance. */
  readonly flows: Action<any, any, any>[] = [];

  get apiStability() {
    return this.registry.apiStability;
  }

  constructor(options?: GenkitOptions) {
    this.options = options || {};
    this.registry = new BrowserRegistry();
    if (this.options.context) {
      this.registry.context = this.options.context;
    }
    this.configure();
  }

  /**
   * Defines and registers a flow function.
   */
  defineFlow<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    S extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    config: FlowConfig<I, O, S> | string,
    fn: FlowFn<I, O, S>
  ): Action<I, O, S> {
    const flow = defineFlow(this.registry, config, fn);
    this.flows.push(flow);
    return flow;
  }

  /**
   * Defines and registers a tool.
   *
   * Tools can be passed to models by name or value during `generate` calls to be called automatically based on the prompt and situation.
   */
  defineTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    config: ToolConfig<I, O>,
    fn: ToolFn<I, O>
  ): ToolAction<I, O> {
    return defineTool(this.registry, config, fn);
  }

  /**
   * Defines a dynamic tool. Dynamic tools are just like regular tools ({@link Genkit.defineTool}) but will not be registered in the
   * Genkit registry and can be defined dynamically at runtime.
   */
  dynamicTool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
    config: ToolConfig<I, O>,
    fn?: ToolFn<I, O>
  ): ToolAction<I, O> {
    return dynamicTool(config, fn).attach(this.registry) as ToolAction<I, O>;
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
   * Defines and registers a prompt based on a function.
   *
   * This is an alternative to defining and importing a .prompt file, providing
   * the most advanced control over how the final request to the model is made.
   *
   * @param options - Prompt metadata including model, model params,
   * input/output schemas, etc
   * @param fn - A function that returns a {@link GenerateRequest}. Any config
   * parameters specified by the {@link GenerateRequest} will take precedence
   * over any parameters specified by `options`.
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
    options: PromptConfig<I, O, CustomOptions>,
    /** @deprecated use `options.messages` with a template string instead. */
    templateOrFn?: string | PromptFn<I>
  ): ExecutablePrompt<z.infer<I>, O, CustomOptions> {
    // For backwards compatibility...
    if (templateOrFn) {
      if (options.messages) {
        throw new GenkitError({
          status: 'INVALID_ARGUMENT',
          message:
            'Cannot specify template/function argument and `options.messages` at the same time',
        });
      }
      if (typeof templateOrFn === 'string') {
        return definePrompt(this.registry, {
          ...options,
          messages: templateOrFn,
        });
      } else {
        // it's the PromptFn
        return definePrompt(this.registry, {
          ...options,
          messages: async (input) => {
            const response = await (
              templateOrFn as PromptFn<z.infer<I>, CustomOptions>
            )(input);
            return response.messages;
          },
        });
      }
    }
    return definePrompt(this.registry, options);
  }

  /**
   * create a handlebards helper (https://handlebarsjs.com/guide/block-helpers.html) to be used in dotpormpt templates.
   */
  defineHelper(name: string, fn: Handlebars.HelperDelegate): void {
    defineHelper(this.registry, name, fn);
  }

  /**
   * Creates a handlebars partial (https://handlebarsjs.com/guide/partials.html) to be used in dotpormpt templates.
   */
  definePartial(name: string, source: string): void {
    definePartial(this.registry, name, source);
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
   * const { response, stream } = ai.generateStream('hi');
   * for await (const chunk of stream) {
   *   console.log(chunk.text);
   * }
   * console.log((await response).text);
   * ```
   */
  generateStream<O extends z.ZodTypeAny = z.ZodTypeAny>(
    strPrompt: string
  ): GenerateStreamResponse<z.infer<O>>;

  /**
   * Make a streaming generate call to the default model with a multipart request.
   *
   * ```ts
   * const ai = genkit({
   *   plugins: [googleAI()],
   *   model: gemini15Flash, // default model
   * })
   *
   * const { response, stream } = ai.generateStream([
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
  ): GenerateStreamResponse<z.infer<O>>;

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
   * const { response, stream } = ai.generateStream({
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
  ): GenerateStreamResponse<z.infer<O>>;

  generateStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options:
      | string
      | Part[]
      | GenerateStreamOptions<O, CustomOptions>
      | PromiseLike<GenerateStreamOptions<O, CustomOptions>>
  ): GenerateStreamResponse<z.infer<O>> {
    if (typeof options === 'string' || Array.isArray(options)) {
      options = { prompt: options };
    }
    return generateStream(this.registry, options);
  }
  /**
   * A flow step that executes the provided function. Each run step is recorded separately in the trace.
   *
   * ```ts
   * ai.defineFlow('hello', async() => {
   *   await ai.run('step1', async () => {
   *     // ... step 1
   *   });
   *   await ai.run('step2', async () => {
   *     // ... step 2
   *   });
   *   return result;
   * })
   * ```
   */
  run<T>(name: string, func: () => Promise<T>): Promise<T>;

  /**
   * A flow step that executes the provided function. Each run step is recorded separately in the trace.
   *
   * ```ts
   * ai.defineFlow('hello', async() => {
   *   await ai.run('step1', async () => {
   *     // ... step 1
   *   });
   *   await ai.run('step2', async () => {
   *     // ... step 2
   *   });
   *   return result;
   * })
   */
  run<T>(
    name: string,
    input: any,
    func: (input?: any) => Promise<T>
  ): Promise<T>;

  run<T>(
    name: string,
    funcOrInput: () => Promise<T> | any,
    maybeFunc?: (input?: any) => Promise<T>
  ): Promise<T> {
    if (maybeFunc) {
      return run(name, funcOrInput, maybeFunc, this.registry);
    }
    return run(name, funcOrInput, this.registry);
  }

  /**
   * Returns current action (or flow) invocation context. Can be used to access things like auth
   * data set by HTTP server frameworks. If invoked outside of an action (e.g. flow or tool) will
   * return `undefined`.
   */
  currentContext(): ActionContext | undefined {
    return getContext(this);
  }

  /**
   * Configures the Genkit instance.
   */
  private configure() {
    const activeRegistry = this.registry;
    defineGenerateAction(activeRegistry);
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
    plugins.forEach((plugin) => {
      const loadedPlugin = plugin(this as any);
      logger.debug(`Registering plugin ${loadedPlugin.name}...`);
      activeRegistry.registerPluginProvider(loadedPlugin.name, {
        name: loadedPlugin.name,
        async initializer() {
          logger.debug(`Initializing plugin ${loadedPlugin.name}:`);
          await loadedPlugin.initializer();
        },
        async resolver(action: ActionType, target: string) {
          if (loadedPlugin.resolver) {
            await loadedPlugin.resolver(action, target);
          }
        },
        async listActions() {
          if (loadedPlugin.listActions) {
            return await loadedPlugin.listActions();
          }
          return [];
        },
      });
    });
  }

  /**
   * Stops all servers.
   */
  async stopServers() {}

  prompt<
    I extends z.ZodTypeAny = z.ZodTypeAny,
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
  >(
    name: string,
    options?: { variant?: string }
  ): ExecutablePrompt<z.infer<I>, O, CustomOptions> {
    throw new Error('Method not implemented.');
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

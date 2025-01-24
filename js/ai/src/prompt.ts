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
  Action,
  defineAction,
  GenkitError,
  JSONSchema7,
  stripUndefinedProps,
  z,
} from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { Message as DpMessage, PromptFunction } from 'dotprompt';
import { existsSync, readdirSync, readFileSync } from 'fs';
import { basename, join, resolve } from 'path';
import { DocumentData } from './document.js';
import {
  generate,
  GenerateOptions,
  GenerateResponse,
  generateStream,
  GenerateStreamResponse,
  OutputOptions,
  toGenerateRequest,
  ToolChoice,
} from './generate.js';
import { Message } from './message.js';
import {
  GenerateRequest,
  GenerateRequestSchema,
  GenerateResponseChunkSchema,
  GenerateResponseSchema,
  MessageData,
  ModelAction,
  ModelArgument,
  ModelMiddleware,
  ModelReference,
  Part,
} from './model.js';
import { getCurrentSession, Session } from './session.js';
import { ToolAction, ToolArgument } from './tool.js';

/**
 * Prompt action.
 */
export type PromptAction<I extends z.ZodTypeAny = z.ZodTypeAny> = Action<
  I,
  typeof GenerateRequestSchema,
  z.ZodNever
> & {
  __action: {
    metadata: {
      type: 'prompt';
    };
  };
  __executablePrompt: ExecutablePrompt<I>;
};

/**
 * Prompt action.
 */
export type ExecutablePromptAction<I extends z.ZodTypeAny = z.ZodTypeAny> =
  Action<
    I,
    typeof GenerateResponseSchema,
    typeof GenerateResponseChunkSchema
  > & {
    __action: {
      metadata: {
        type: 'executablePrompt';
      };
    };
    __executablePrompt: ExecutablePrompt<I>;
  };

/**
 * Configuration for a prompt action.
 */
export interface PromptConfig<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  name: string;
  variant?: string;
  model?: ModelArgument<CustomOptions>;
  config?: z.infer<CustomOptions>;
  description?: string;
  input?: {
    schema?: I;
    jsonSchema?: JSONSchema7;
  };
  system?: string | Part | Part[] | PartsResolver<z.infer<I>>;
  prompt?: string | Part | Part[] | PartsResolver<z.infer<I>>;
  messages?: string | MessageData[] | MessagesResolver<z.infer<I>>;
  docs?: DocumentData[] | DocsResolver<z.infer<I>>;
  output?: OutputOptions<O>;
  maxTurns?: number;
  returnToolRequests?: boolean;
  metadata?: Record<string, any>;
  tools?: ToolArgument[];
  toolChoice?: ToolChoice;
  use?: ModelMiddleware[];
}

/**
 * Generate options of a prompt.
 */
export type PromptGenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = Omit<GenerateOptions<O, CustomOptions>, 'prompt' | 'system'>;

/**
 * A prompt that can be executed as a function.
 */
export interface ExecutablePrompt<
  I = undefined,
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
  (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>>;

  /**
   * Generates a response by rendering the prompt template with given user input and then calling the model.
   * @param input Prompt inputs.
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns the model response as a promise of `GenerateStreamResponse`.
   */
  stream(
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): GenerateStreamResponse<z.infer<O>>;

  /**
   * Renders the prompt template based on user input.
   *
   * @param opt Options for the prompt template, including user input variables and custom model configuration options.
   * @returns a `GenerateOptions` object to be used with the `generate()` function from @genkit-ai/ai.
   */
  render(
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<GenerateOptions<O, CustomOptions>>;

  /**
   * Returns the prompt usable as a tool.
   */
  asTool(): Promise<ToolAction>;
}

export type PartsResolver<I, S = any> = (
  input: I,
  options: {
    state?: S;
  }
) => Part[] | Promise<string | Part | Part[]>;

export type MessagesResolver<I, S = any> = (
  input: I,
  options: {
    history?: MessageData[];
    state?: S;
  }
) => MessageData[] | Promise<MessageData[]>;

export type DocsResolver<I, S = any> = (
  input: I,
  options: {
    state?: S;
  }
) => DocumentData[] | Promise<DocumentData[]>;

interface PromptCache {
  userPrompt?: PromptFunction;
  system?: PromptFunction;
  messages?: PromptFunction;
}

/**
 * Defines a prompt which can be used to generate content or render a request.
 *
 * @returns The new `ExecutablePrompt`.
 */
export function definePrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  options: PromptConfig<I, O, CustomOptions>
): ExecutablePrompt<z.infer<I>, O, CustomOptions> {
  const promptCache = {} as PromptCache;

  const renderOptionsFn = async (
    input: z.infer<I>,
    renderOptions: PromptGenerateOptions<O, CustomOptions> | undefined
  ): Promise<GenerateOptions> => {
    const messages: MessageData[] = [];
    renderOptions = { ...renderOptions }; // make a copy, we will be trimming
    const session = getCurrentSession(registry);

    // order of these matters:
    await renderSystemPrompt(
      registry,
      session,
      input,
      messages,
      options,
      promptCache
    );
    await renderMessages(
      registry,
      session,
      input,
      messages,
      options,
      renderOptions,
      promptCache
    );
    await renderUserPrompt(
      registry,
      session,
      input,
      messages,
      options,
      promptCache
    );

    let docs: DocumentData[] | undefined;
    if (typeof options.docs === 'function') {
      docs = await options.docs(input, {
        state: session?.state,
      });
    } else {
      docs = options.docs;
    }

    return stripUndefinedProps({
      model: options.model,
      maxTurns: options.maxTurns,
      messages,
      docs,
      tools: options.tools,
      returnToolRequests: options.returnToolRequests,
      toolChoice: options.toolChoice,
      output: options.output,
      use: options.use,
      ...stripUndefinedProps(renderOptions),
      config: {
        ...options?.config,
        ...renderOptions?.config,
      },
    });
  };
  const rendererAction = defineAction(
    registry,
    {
      name: `${options.name}${options.variant ? `.${options.variant}` : ''}`,
      inputJsonSchema: options.input?.jsonSchema,
      inputSchema: options.input?.schema,
      description: options.description,
      actionType: 'prompt',
      metadata: {
        prompt: {
          config: options.config,
          input: {
            schema: options.input ? toJsonSchema(options.input) : undefined,
          },
          name: options.name,
          model: modelName(options.model),
        },
        ...options.metadata,
        type: 'prompt',
      },
    },
    async (input: z.infer<I>): Promise<GenerateRequest<z.ZodTypeAny>> => {
      return toGenerateRequest(
        registry,
        await renderOptionsFn(input, undefined)
      );
    }
  ) as PromptAction<I>;
  const executablePromptAction = defineAction(
    registry,
    {
      name: `${options.name}${options.variant ? `.${options.variant}` : ''}`,
      inputJsonSchema: options.input?.jsonSchema,
      inputSchema: options.input?.schema,
      description: options.description,
      actionType: 'executable-prompt',
      metadata: { ...(options.metadata || { prompt: {} }), type: 'prompt' },
    },
    async (input: z.infer<I>, { sendChunk }): Promise<GenerateResponse> => {
      return await generate(registry, {
        ...(await renderOptionsFn(input, undefined)),
        onChunk: sendChunk,
      });
    }
  ) as ExecutablePromptAction<I>;

  const executablePrompt = wrapInExecutablePrompt(
    registry,
    renderOptionsFn,
    rendererAction
  );

  executablePromptAction.__executablePrompt =
    executablePrompt as never as ExecutablePrompt<z.infer<I>>;
  rendererAction.__executablePrompt =
    executablePrompt as never as ExecutablePrompt<z.infer<I>>;

  return executablePrompt;
}

function wrapInExecutablePrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  renderOptionsFn: (
    input: z.infer<I>,
    renderOptions: PromptGenerateOptions<O, CustomOptions> | undefined
  ) => Promise<GenerateOptions>,
  rendererAction: PromptAction<I>
) {
  const executablePrompt = (async (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> => {
    return generate(registry, {
      ...(await renderOptionsFn(input, opts)),
    });
  }) as ExecutablePrompt<z.infer<I>, O, CustomOptions>;

  executablePrompt.render = async (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<GenerateOptions<O, CustomOptions>> => {
    return {
      ...(await renderOptionsFn(input, opts)),
    } as GenerateOptions<O, CustomOptions>;
  };

  executablePrompt.stream = (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): GenerateStreamResponse<z.infer<O>> => {
    return generateStream(registry, renderOptionsFn(input, opts));
  };

  executablePrompt.asTool = async (): Promise<ToolAction<I, O>> => {
    return rendererAction as unknown as ToolAction<I, O>;
  };
  return executablePrompt;
}

async function renderSystemPrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  session: Session | undefined,
  input: z.infer<I>,
  messages: MessageData[],
  options: PromptConfig<I, O, CustomOptions>,
  promptCache: PromptCache
) {
  if (typeof options.system === 'function') {
    messages.push({
      role: 'system',
      content: normalizeParts(
        await options.system(input, { state: session?.state })
      ),
    });
  } else if (typeof options.system === 'string') {
    // memoize compiled prompt
    if (!promptCache.system) {
      promptCache.system = await registry.dotpromptEnv.compile(options.system);
    }
    messages.push({
      role: 'system',
      content: await renderDotpromptToParts(promptCache.system, input, session),
    });
  } else if (options.system) {
    messages.push({
      role: 'system',
      content: normalizeParts(options.system),
    });
  }
}

async function renderMessages<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  session: Session | undefined,
  input: z.infer<I>,
  messages: MessageData[],
  options: PromptConfig<I, O, CustomOptions>,
  renderOptions: PromptGenerateOptions<O, CustomOptions>,
  promptCache: PromptCache
) {
  if (options.messages) {
    if (typeof options.messages === 'function') {
      messages.push(
        ...(await options.messages(input, {
          state: session?.state,
          history: renderOptions?.messages,
        }))
      );
    } else if (typeof options.messages === 'string') {
      // memoize compiled prompt
      if (!promptCache.messages) {
        promptCache.messages = await registry.dotpromptEnv.compile(
          options.messages
        );
      }
      const rendered = await promptCache.messages({
        input,
        context: { state: session?.state },
        messages: renderOptions?.messages?.map((m) =>
          Message.parseData(m)
        ) as DpMessage[],
      });
      messages.push(...rendered.messages);
    } else {
      messages.push(...options.messages);
    }
  } else {
    if (renderOptions.messages) {
      messages.push(...renderOptions.messages);
    }
  }
  if (renderOptions?.messages) {
    // delete messages from opts so that we don't override messages downstream
    delete renderOptions.messages;
  }
}

async function renderUserPrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  session: Session | undefined,
  input: z.infer<I>,
  messages: MessageData[],
  options: PromptConfig<I, O, CustomOptions>,
  promptCache: PromptCache
) {
  if (typeof options.prompt === 'function') {
    messages.push({
      role: 'user',
      content: normalizeParts(
        await options.prompt(input, { state: session?.state })
      ),
    });
  } else if (typeof options.prompt === 'string') {
    // memoize compiled prompt
    if (!promptCache.userPrompt) {
      promptCache.userPrompt = await registry.dotpromptEnv.compile(
        options.prompt
      );
    }
    messages.push({
      role: 'user',
      content: await renderDotpromptToParts(
        promptCache.userPrompt,
        input,
        session
      ),
    });
  } else if (options.prompt) {
    messages.push({
      role: 'user',
      content: normalizeParts(options.prompt),
    });
  }
}

function modelName(
  modelArg: ModelArgument<any> | undefined
): string | undefined {
  if (modelArg === undefined) {
    return undefined;
  }
  if (typeof modelArg === 'string') {
    return modelArg;
  }
  if ((modelArg as ModelReference<any>).name) {
    return (modelArg as ModelReference<any>).name;
  }
  return (modelArg as ModelAction).__action.name;
}

function normalizeParts(parts: string | Part | Part[]): Part[] {
  if (Array.isArray(parts)) return parts;
  if (typeof parts === 'string') {
    return [
      {
        text: parts,
      },
    ];
  }
  return [parts as Part];
}

async function renderDotpromptToParts(
  promptFn: PromptFunction,
  input: any,
  session?: Session
): Promise<Part[]> {
  const renderred = await promptFn({
    input,
    context: { state: session?.state },
  });
  if (renderred.messages.length !== 1) {
    throw new Error('parts tempate must produce only one message');
  }
  return renderred.messages[0].content;
}

/**
 * Checks whether the provided object is an executable prompt.
 */
export function isExecutablePrompt(obj: any): boolean {
  return (
    !!(obj as ExecutablePrompt)?.render &&
    !!(obj as ExecutablePrompt)?.asTool &&
    !!(obj as ExecutablePrompt)?.stream
  );
}

export async function loadPromptFolder(
  registry: Registry,
  dir: string = './prompts',
  ns: string
): Promise<void> {
  const promptsPath = resolve(dir);
  if (existsSync(promptsPath)) {
    const dirEnts = readdirSync(promptsPath, {
      withFileTypes: true,
      recursive: true,
    });
    for (const dirEnt of dirEnts) {
      if (dirEnt.isFile() && dirEnt.name.endsWith('.prompt')) {
        if (dirEnt.name.startsWith('_')) {
          const partialName = dirEnt.name.substring(1, dirEnt.name.length - 7);
          definePartial(
            registry,
            partialName,
            readFileSync(join(dirEnt.path, dirEnt.name), {
              encoding: 'utf8',
            })
          );
          logger.debug(
            `Registered Dotprompt partial "${partialName}" from "${join(dirEnt.path, dirEnt.name)}"`
          );
        } else {
          // If this prompt is in a subdirectory, we need to include that
          // in the namespace to prevent naming conflicts.
          let prefix = '';
          if (promptsPath !== dirEnt.path) {
            prefix = dirEnt.path
              .replace(`${promptsPath}/`, '')
              .replace(/\//g, '-');
          }
          await loadPrompt(registry, dirEnt.path, dirEnt.name, prefix, ns);
        }
      }
    }
  }
}

export function definePartial(
  registry: Registry,
  name: string,
  source: string
) {
  registry.dotpromptEnv.definePartial(name, source);
}

export function defineHelper(
  registry: Registry,
  name: string,
  fn: Handlebars.HelperDelegate
) {
  registry.dotpromptEnv.defineHelper(name, fn);
}

async function loadPrompt(
  registry: Registry,
  path: string,
  filename: string,
  prefix = '',
  ns = 'dotprompt'
): Promise<void> {
  let name = `${prefix ? `${prefix}-` : ''}${basename(filename, '.prompt')}`;
  let variant: string | null = null;
  if (name.includes('.')) {
    const parts = name.split('.');
    name = parts[0];
    variant = parts[1];
  }
  const source = readFileSync(join(path, filename), 'utf8');
  const parsedPrompt = registry.dotpromptEnv.parse(source);
  const promptMetadata =
    await registry.dotpromptEnv.renderMetadata(parsedPrompt);
  if (variant) {
    promptMetadata.variant = variant;
  }
  definePrompt(registry, {
    name: registryDefinitionKey(name, variant ?? undefined, ns),
    model: promptMetadata.model,
    config: promptMetadata.config,
    tools: promptMetadata.tools,
    description: promptMetadata.description,
    output: {
      jsonSchema: promptMetadata.output?.schema,
      format: promptMetadata.output?.format,
    },
    input: {
      jsonSchema: promptMetadata.input?.schema,
    },
    metadata: {
      ...promptMetadata.metadata,
      type: 'prompt',
      prompt: {
        ...promptMetadata,
        template: source,
      },
    },
    maxTurns: promptMetadata.raw?.['maxTurns'],
    toolChoice: promptMetadata.raw?.['toolChoice'],
    returnToolRequests: promptMetadata.raw?.['returnToolRequests'],
    messages: parsedPrompt.template,
  });
}

export async function prompt<
  I = undefined,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  name: string,
  options?: { variant?: string; dir?: string }
): Promise<ExecutablePrompt<I, O, CustomOptions>> {
  return await lookupPrompt<I, O, CustomOptions>(
    registry,
    name,
    options?.variant
  );
}

function registryLookupKey(name: string, variant?: string, ns?: string) {
  return `/prompt/${registryDefinitionKey(name, variant, ns)}`;
}

async function lookupPrompt<
  I = undefined,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  name: string,
  variant?: string
): Promise<ExecutablePrompt<I, O, CustomOptions>> {
  let registryPrompt =
    (await registry.lookupAction(registryLookupKey(name, variant))) ||
    (await registry.lookupAction(
      registryLookupKey(name, variant, 'dotprompt')
    ));
  if (registryPrompt) {
    return (registryPrompt as PromptAction)
      .__executablePrompt as never as ExecutablePrompt<I, O, CustomOptions>;
  }
  throw new GenkitError({
    status: 'NOT_FOUND',
    message: `Prompt ${name + (variant ? ` (variant ${variant})` : '')} not found`,
  });
}

function registryDefinitionKey(name: string, variant?: string, ns?: string) {
  // "ns/prompt.variant" where ns and variant are optional
  return `${ns ? `${ns}/` : ''}${name}${variant ? `.${variant}` : ''}`;
}

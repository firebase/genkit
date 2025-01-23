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
  z,
} from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { Message as DpMessage, PromptFunction } from 'dotprompt';
import { existsSync, readdir, readFileSync } from 'fs';
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
 * Prompt implementation function signature.
 */
export type PromptFn<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
> = (input: z.infer<I>) => Promise<GenerateRequest<CustomOptionsSchema>>;

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
  system?: string | Part | Part[] | PartsGenerator<z.infer<I>>;
  prompt?: string | Part | Part[] | PartsGenerator<z.infer<I>>;
  messages?: string | MessageData[] | MessageGenerator<z.infer<I>>;
  docs?: DocumentData[] | DocumentGenerator<z.infer<I>>;
  output?: OutputOptions<O>;
  maxTurns?: number;
  returnToolRequests?: boolean;
  metadata?: Record<string, any>;
  tools?: ToolArgument[];
  toolChoice?: ToolChoice;
  use?: ModelMiddleware[];
}

/**
 * Checks whether provided object is a prompt.
 */
export function isPrompt(arg: any): boolean {
  return (
    typeof arg === 'function' &&
    (arg as any).__action?.metadata?.type === 'prompt'
  );
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

export type PartsGenerator<I, S = any> = (
  input: I,
  options: {
    state?: S;
  }
) => Part[] | Promise<string | Part | Part[]>;

export type MessageGenerator<I, S = any> = (
  input: I,
  options: {
    history?: MessageData[];
    state?: S;
  }
) => MessageData[] | Promise<MessageData[]>;

export type DocumentGenerator<I, S = any> = (
  input: I,
  options: {
    state?: S;
  }
) => DocumentData[] | Promise<DocumentData[]>;

/**
 * Defines and registers a prompt action. The action can be called to obtain
 * a `GenerateRequest` which can be passed to a model action. The given
 * `PromptFn` can perform any action needed to create the request such as rendering
 * a template or fetching a prompt from a database.
 *
 * @returns The new `PromptAction`.
 */
export function definePrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  options: PromptConfig<I, O, CustomOptions>
): ExecutablePrompt<z.infer<I>, O, CustomOptions> {
  let compiledPrompt: PromptFunction;
  let compiledSystem: PromptFunction;
  let compiledMessages: PromptFunction;
  const renderOptions = async (
    input: z.infer<I>,
    opts: PromptGenerateOptions<O, CustomOptions> | undefined
  ): Promise<GenerateOptions> => {
    const session = getCurrentSession(registry);
    let messages: MessageData[] = [];
    opts = { ...opts }; // make a copy, we will be trimming

    if (typeof options.system === 'function') {
      messages.push({
        role: 'system',
        content: normalizeParts(
          await options.system(input, { state: session?.state })
        ),
      });
    } else if (typeof options.system === 'string') {
      // memoize compiled prompt
      if (!compiledSystem) {
        compiledSystem = await registry.dotpromptEnv.compile(options.system);
      }
      messages.push({
        role: 'system',
        content: await renderDotpromptToParts(compiledSystem, input, session),
      });
    } else if (options.system) {
      messages.push({
        role: 'system',
        content: normalizeParts(options.system),
      });
    }

    if (options.messages) {
      if (typeof options.messages === 'function') {
        messages.push(
          ...(await options.messages(input, {
            state: session?.state,
            history: opts?.messages,
          }))
        );
      } else if (typeof options.messages === 'string') {
        // memoize compiled prompt
        if (!compiledMessages) {
          compiledMessages = await registry.dotpromptEnv.compile(
            options.messages
          );
        }
        const rendered = await compiledMessages({
          input,
          context: { state: session?.state },
          messages: opts?.messages?.map((m) =>
            Message.parseData(m)
          ) as DpMessage[],
        });
        messages.push(...rendered.messages);
      } else {
        messages.push(...options.messages);
      }
    } else {
      if (opts.messages) {
        messages.push(...opts.messages);
      }
    }
    if (opts?.messages) {
      // delete messages from opts so that we don't override messages
      delete opts.messages;
    }

    if (typeof options.prompt === 'function') {
      messages.push({
        role: 'user',
        content: normalizeParts(
          await options.prompt(input, { state: session?.state })
        ),
      });
    } else if (typeof options.prompt === 'string') {
      // memoize compiled prompt
      if (!compiledPrompt) {
        compiledPrompt = await registry.dotpromptEnv.compile(options.prompt);
      }
      messages.push({
        role: 'user',
        content: await renderDotpromptToParts(compiledPrompt, input, session),
      });
    } else if (options.prompt) {
      messages.push({
        role: 'user',
        content: normalizeParts(options.prompt),
      });
    }

    let docs: DocumentData[] | undefined;
    if (typeof options.docs === 'function') {
      docs = await options.docs(input, { state: session?.state });
    } else {
      docs = options.docs;
    }

    return {
      model: options.model,
      tools: options.tools,
      maxTurns: options.maxTurns,
      docs,
      messages,
      returnToolRequests: options.returnToolRequests,
      output: options.output,
      use: options.use,
      ...stripUndefined(opts),
      config: {
        ...options?.config,
        ...opts?.config,
      },
    };
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
      //outputSchema: GenerateRequestSchema,
    },
    async (input: z.infer<I>): Promise<GenerateRequest<z.ZodTypeAny>> => {
      return toGenerateRequest(registry, await renderOptions(input, undefined));
    }
  ) as PromptAction<I>;
  const executablePromptAction = defineAction(
    registry,
    {
      name: `${options.name}${options.variant ? `.${options.variant}` : ''}`,
      inputJsonSchema: options.input?.jsonSchema,
      inputSchema: options.input?.schema,
      description: options.description,
      //outputSchema: GenerateResponseSchema,
      actionType: 'executable-prompt',
      metadata: { ...(options.metadata || { prompt: {} }), type: 'prompt' },
    },
    async (input: z.infer<I>, { sendChunk }): Promise<GenerateResponse> => {
      return await generate(registry, {
        ...(await renderOptions(input, undefined)),
        onChunk: sendChunk,
      });
    }
  ) as ExecutablePromptAction<I>;

  const executablePrompt = (async (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> => {
    return generate(registry, {
      ...(await renderOptions(input, opts)),
    });
  }) as ExecutablePrompt<z.infer<I>, O, CustomOptions>;

  executablePrompt.render = async (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<GenerateOptions<O, CustomOptions>> => {
    const rendered = await renderOptions(input, opts);
    return {
      ...(await renderOptions(input, opts)),
    } as GenerateOptions<O, CustomOptions>;
  };

  executablePrompt.stream = (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): GenerateStreamResponse<z.infer<O>> => {
    return generateStream(registry, renderOptions(input, opts));
  };

  executablePrompt.asTool = async (): Promise<ToolAction<I, O>> => {
    return rendererAction as unknown as ToolAction<I, O>;
  };

  executablePromptAction.__executablePrompt =
    executablePrompt as never as ExecutablePrompt<z.infer<I>>;
  rendererAction.__executablePrompt =
    executablePrompt as never as ExecutablePrompt<z.infer<I>>;

  return executablePrompt;
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

export type PromptArgument<I extends z.ZodTypeAny = z.ZodTypeAny> =
  | string
  | PromptAction<I>;

/**
 * This veneer renders a `PromptAction` into a `GenerateOptions` object.
 *
 * @returns A promise of an options object for use with the `generate()` function.
 */
export async function renderPrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  registry: Registry,
  params: {
    prompt: PromptArgument<I>;
    input: z.infer<I>;
    docs?: DocumentData[];
    model: ModelArgument<CustomOptions>;
    config?: z.infer<CustomOptions>;
  }
): Promise<GenerateOptions<O, CustomOptions>> {
  let prompt: PromptAction<I>;
  if (typeof params.prompt === 'string') {
    prompt = await registry.lookupAction(`/prompt/${params.prompt}`);
  } else {
    prompt = params.prompt as PromptAction<I>;
  }
  const rendered = (await prompt(
    params.input
  )) as GenerateRequest<CustomOptions>;
  return {
    model: params.model,
    config: { ...(rendered.config || {}), ...params.config },
    messages: rendered.messages.slice(0, rendered.messages.length - 1),
    prompt: rendered.messages[rendered.messages.length - 1].content,
    docs: params.docs,
    output: {
      format: rendered.output?.format,
      schema: rendered.output?.schema,
    },
    tools: rendered.tools || [],
  } as GenerateOptions<O, CustomOptions>;
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

function stripUndefined(input: any) {
  if (
    input === undefined ||
    Array.isArray(input) ||
    typeof input !== 'object'
  ) {
    return input;
  }
  const out = {};
  for (const key in input) {
    if (input[key] !== undefined) {
      out[key] = stripUndefined(input[key]);
    }
  }
  return out;
}

export async function loadPromptFolder(
  registry: Registry,
  dir: string = './prompts',
  ns: string
): Promise<void> {
  const promptsPath = resolve(dir);
  return new Promise<void>((resolve, reject) => {
    if (existsSync(promptsPath)) {
      readdir(
        promptsPath,
        {
          withFileTypes: true,
          recursive: true,
        },
        (err, dirEnts) => {
          if (err) {
            reject(err);
          } else {
            dirEnts.forEach(async (dirEnt) => {
              if (dirEnt.isFile() && dirEnt.name.endsWith('.prompt')) {
                if (dirEnt.name.startsWith('_')) {
                  const partialName = dirEnt.name.substring(
                    1,
                    dirEnt.name.length - 7
                  );
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
                  loadPrompt(registry, dirEnt.path, dirEnt.name, prefix, ns);
                }
              }
            });
            resolve();
          }
        }
      );
    } else {
      resolve();
    }
  });
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

function loadPrompt(
  registry: Registry,
  path: string,
  filename: string,
  prefix = '',
  ns = 'dotprompt'
): void {
  let name = `${prefix ? `${prefix}-` : ''}${basename(filename, '.prompt')}`;
  let variant: string | null = null;
  if (name.includes('.')) {
    const parts = name.split('.');
    name = parts[0];
    variant = parts[1];
  }
  const source = readFileSync(join(path, filename), 'utf8');
  const prompt = registry.dotpromptEnv.parse(source);
  if (variant) {
    prompt.variant = variant;
  }
  definePrompt(registry, {
    name: registryDefinitionKey(name, variant ?? undefined, ns),
    config: prompt.config,
    tools: prompt.tools,
    description: prompt.description,
    input: {
      jsonSchema: prompt.input?.schema,
    },
    metadata: {
      type: 'prompt',
      prompt: prompt,
    },
    messages: prompt.template,
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

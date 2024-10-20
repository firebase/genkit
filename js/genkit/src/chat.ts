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
  ExecutablePrompt,
  GenerateOptions,
  GenerateResponse,
  GenerateStreamOptions,
  GenerateStreamResponse,
  GenerationCommonConfigSchema,
  MessageData,
  Part,
  ToolArgument,
} from '@genkit-ai/ai';
import { resolveTools } from '@genkit-ai/ai/tool';
import { z } from '@genkit-ai/core';
import { Genkit } from './genkit';
import { runWithRegistry } from './registry';
import { BaseGenerateOptions, Session, SessionStore } from './session';
import { runInNewSpan } from './tracing';

export const MAIN_THREAD = 'main';

export type ExtendedToolArgument = ToolArgument | ExecutablePrompt;

export type ChatGenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = Omit<GenerateOptions<O, CustomOptions>, 'tools'> & {
  tools?: ExtendedToolArgument[];
};

export interface PromptRenderOptions<I> {
  prompt: ExecutablePrompt<I>;
  input?: I;
}

export type ChatOptions<
  I = undefined,
  S extends z.ZodTypeAny = z.ZodTypeAny,
> = (PromptRenderOptions<I> | BaseGenerateOptions) & {
  store?: SessionStore<S>;
  sessionId?: string;
};

/**
 * Chat encapsulates a statful execution environment for chat.
 * Chat session executed within a session in this environment will have acesss to
 * session convesation history.
 *
 * ```ts
 * const ai = genkit({...});
 * const chat = ai.chat(); // create a Chat
 * let response = await chat.send('hi, my name is Genkit');
 * response = await chat.send('what is my name?'); // chat history aware conversation
 * ```
 */
export class Chat<S extends z.ZodTypeAny = z.ZodTypeAny> {
  private requestBase?: Promise<BaseGenerateOptions>;
  readonly sessionId: string;
  readonly schema?: S;
  private _messages?: MessageData[];
  private threadName: string;

  constructor(
    readonly session: Session<S>,
    requestBase: Promise<BaseGenerateOptions>,
    options: {
      id: string;
      thread: string;
      messages?: MessageData[];
    }
  ) {
    this.sessionId = options.id;
    this.threadName = options.thread;
    this.requestBase = requestBase?.then((rb) => {
      const requestBase = { ...rb };
      // this is handling dotprompt render case
      if (requestBase && requestBase['prompt']) {
        const basePrompt = requestBase['prompt'] as string | Part | Part[];
        let promptMessage: MessageData;
        if (typeof basePrompt === 'string') {
          promptMessage = {
            role: 'user',
            content: [{ text: basePrompt }],
          };
        } else if (Array.isArray(basePrompt)) {
          promptMessage = {
            role: 'user',
            content: basePrompt,
          };
        } else {
          promptMessage = {
            role: 'user',
            content: [basePrompt],
          };
        }
        requestBase.messages = [...(requestBase.messages ?? []), promptMessage];
      }
      requestBase.messages = [
        ...(options.messages ?? []),
        ...(requestBase.messages ?? []),
      ];
      this._messages = requestBase.messages;
      return requestBase;
    });
    this._messages = options.messages;
  }

  async send<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | ChatGenerateOptions<O, CustomOptions>
  ): Promise<GenerateResponse<z.infer<O>>> {
    return runInNewSpan({ metadata: { name: 'send' } }, async () => {
      let resolvedOptions;
      let streamingCallback = undefined;

      // string
      if (typeof options === 'string') {
        resolvedOptions = {
          prompt: options,
        } as ChatGenerateOptions<O, CustomOptions>;
      } else if (Array.isArray(options)) {
        // Part[]
        resolvedOptions = {
          prompt: options,
        } as ChatGenerateOptions<O, CustomOptions>;
      } else {
        resolvedOptions = options as ChatGenerateOptions<O, CustomOptions>;
        streamingCallback = resolvedOptions.streamingCallback;
      }
      let request: GenerateOptions = {
        ...(await this.requestBase),
        messages: this.messages,
        ...resolvedOptions,
      };
      request.tools = resolveExecutablePromptTools(
        request.tools as ExtendedToolArgument[]
      );
      let response = await this.genkit.generate({
        ...request,
        streamingCallback,
      });
      while (response.toolRequests.length > 0) {
        request = await this.handlePromptToolCalling(response, request.tools!);
        response = await this.genkit.generate({
          ...request,
          streamingCallback,
        });
      }
      await this.updateMessages(response.messages);
      return response;
    });
  }

  private async handlePromptToolCalling(
    response: GenerateResponse,
    tools: ToolArgument[]
  ): Promise<GenerateOptions> {
    // TODO: refactor resolveTools to not rely on runWithRegistry
    return await runWithRegistry(this.genkit.registry, async () => {
      const toolRequest = response.toolRequests[0];
      const resolvedTools = await resolveTools(tools);

      const tool = resolvedTools.find(
        (tool) => tool.__action.name === toolRequest.toolRequest?.name
      );
      if (!tool) {
        throw new Error(`Tool ${toolRequest.toolRequest?.name} not found`);
      }
      const newPreamble = (await tool(
        toolRequest.toolRequest?.input
      )) as GenerateOptions;

      this._messages = [
        ...(tagAsPreamble(newPreamble.messages) ?? []),
        ...(response.messages?.filter((m) => !m?.metadata?.preamble) ?? []),
        {
          role: 'tool',
          content: [
            {
              toolResponse: {
                name: toolRequest.toolRequest.name,
                ref: toolRequest.toolRequest.ref,
                output: `transferred to ${toolRequest.toolRequest.name}`,
              },
            },
          ],
        },
      ];
      this.requestBase = Promise.resolve({
        ...(await this.requestBase),
        messages: newPreamble.messages,
        tools: resolveExecutablePromptTools(newPreamble.tools),
      });
      return {
        ...(await this.requestBase),
        messages: this.messages,
      };
    });
  }

  async sendStream<
    O extends z.ZodTypeAny = z.ZodTypeAny,
    CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
  >(
    options: string | Part[] | GenerateStreamOptions<O, CustomOptions>
  ): Promise<GenerateStreamResponse<z.infer<O>>> {
    // string
    if (typeof options === 'string') {
      options = {
        prompt: options,
      } as GenerateOptions<O, CustomOptions>;
    }
    // Part[]
    if (Array.isArray(options)) {
      options = {
        prompt: options,
      } as GenerateOptions<O, CustomOptions>;
    }
    const { response, stream } = await this.genkit.generateStream({
      ...(await this.requestBase),
      messages: this.messages,
      ...options,
    });

    return {
      response: response.finally(async () => {
        this.updateMessages((await response).messages);
      }),
      stream,
    };
  }

  private get genkit(): Genkit {
    return this.session.genkit;
  }

  get messages(): MessageData[] {
    return this._messages ?? [];
  }

  async updateMessages(messages: MessageData[]): Promise<void> {
    this._messages = messages;
    await this.session.updateMessages(this.threadName, messages);
  }
}

export function resolveExecutablePromptTools(
  tools?: ExtendedToolArgument[]
): ToolArgument[] | undefined {
  return tools?.map((et) => {
    if ((et as ExecutablePrompt).render) {
      return (et as ExecutablePrompt).asTool();
    }
    return et as ToolArgument;
  });
}

export function tagAsPreamble(msgs?: MessageData[]): MessageData[] | undefined {
  if (!msgs) {
    return undefined;
  }
  return msgs.map((m) => ({
    ...m,
    metadata: {
      ...m.metadata,
      preamble: true,
    },
  }));
}

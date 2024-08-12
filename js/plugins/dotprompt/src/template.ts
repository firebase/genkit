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

import { MediaPart, MessageData, Part, Role } from '@genkit-ai/ai/model';
import { DocumentData } from '@genkit-ai/ai/retriever';
import Handlebars from 'handlebars';
import { PromptMetadata } from './metadata.js';

const Promptbars: typeof Handlebars =
  global['dotprompt.handlebars'] || Handlebars.create();
global['dotprompt.handlebars'] = Promptbars;

function jsonHelper(serializable: any, options: { hash: { indent?: number } }) {
  return new Promptbars.SafeString(
    JSON.stringify(serializable, null, options.hash.indent || 0)
  );
}
Promptbars.registerHelper('json', jsonHelper);

function roleHelper(role: string) {
  return new Promptbars.SafeString(`<<<dotprompt:role:${role}>>>`);
}
Promptbars.registerHelper('role', roleHelper);

function historyHelper() {
  return new Promptbars.SafeString('<<<dotprompt:history>>>');
}
Promptbars.registerHelper('history', historyHelper);

function sectionHelper(name: string) {
  return new Promptbars.SafeString(`<<<dotprompt:section ${name}>>>`);
}
Promptbars.registerHelper('section', sectionHelper);

function mediaHelper(options: Handlebars.HelperOptions) {
  return new Promptbars.SafeString(
    `<<<dotprompt:media:url ${options.hash.url}${
      options.hash.contentType ? ` ${options.hash.contentType}` : ''
    }>>>`
  );
}
Promptbars.registerHelper('media', mediaHelper);

const ROLE_REGEX = /(<<<dotprompt:(?:role:[a-z]+|history))>>>/g;

function toMessages(
  renderedString: string,
  options?: { context?: DocumentData[]; history?: MessageData[] }
): MessageData[] {
  let currentMessage: { role: string; source: string } = {
    role: 'user',
    source: '',
  };
  const messageSources: {
    role: string;
    source?: string;
    content?: MessageData['content'];
    metadata?: Record<string, unknown>;
  }[] = [currentMessage];

  for (const piece of renderedString
    .split(ROLE_REGEX)
    .filter((s) => s.trim() !== '')) {
    if (piece.startsWith('<<<dotprompt:role:')) {
      const role = piece.substring(18);
      if (currentMessage.source.trim()) {
        currentMessage = { role, source: '' };
        messageSources.push(currentMessage);
      } else {
        currentMessage.role = role;
      }
    } else if (piece.startsWith('<<<dotprompt:history')) {
      messageSources.push(
        ...(options?.history?.map((m) => {
          return {
            ...m,
            metadata: { ...(m.metadata || {}), purpose: 'history' },
          };
        }) || [])
      );
      currentMessage = { role: 'model', source: '' };
      messageSources.push(currentMessage);
    } else {
      currentMessage.source += piece;
    }
  }

  const messages: MessageData[] = messageSources
    .filter((ms) => ms.content || ms.source)
    .map((m) => {
      const out: MessageData = {
        role: m.role as Role,
        content: m.content || toParts(m.source!),
      };
      if (m.metadata) out.metadata = m.metadata;
      return out;
    });

  if (
    !options?.history ||
    messages.find((m) => m.metadata?.purpose === 'history')
  )
    return messages;

  return [
    ...messages.slice(0, -1),
    ...options.history,
    messages.at(-1),
  ] as MessageData[];
}

const PART_REGEX = /(<<<dotprompt:(?:media:url|section).*?)>>>/g;

function toParts(source: string): Part[] {
  const parts: Part[] = [];
  const pieces = source.split(PART_REGEX).filter((s) => s.trim() !== '');
  for (let i = 0; i < pieces.length; i++) {
    const piece = pieces[i];
    if (piece.startsWith('<<<dotprompt:media:')) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const [_, url, contentType] = piece.split(' ');
      const part: MediaPart = { media: { url } };
      if (contentType) part.media.contentType = contentType;
      parts.push(part);
    } else if (piece.startsWith('<<<dotprompt:section')) {
      const [_, sectionType] = piece.split(' ');
      parts.push({ metadata: { purpose: sectionType, pending: true } });
    } else {
      parts.push({ text: piece });
    }
  }

  return parts;
}

export function compile<Variables = any>(
  source: string,
  metadata: PromptMetadata
) {
  const renderString = Promptbars.compile<Variables>(source, {
    knownHelpers: {
      json: true,
      section: true,
      media: true,
      role: true,
      history: true,
    },
  });

  return (
    input: Variables,
    options?: { context?: DocumentData[]; history?: MessageData[] }
  ) => {
    const renderedString = renderString(input, {
      data: {
        metadata: { prompt: metadata, context: options?.context || null },
      },
    });
    return toMessages(renderedString, options);
  };
}

export function defineHelper(name: string, fn: Handlebars.HelperDelegate) {
  Promptbars.registerHelper(name, fn);
}

export function definePartial(name: string, source: string) {
  Promptbars.registerPartial(name, source);
}

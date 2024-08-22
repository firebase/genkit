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

import { MessageData } from '@genkit/ai/model';

const chatHistory: Record<string, MessageData[]> = {};

export interface HistoryStore {
  load(id: string): Promise<MessageData[] | undefined>;
  save(id: string, history: MessageData[]): Promise<void>;
}

export function inMemoryStore(): HistoryStore {
  return {
    async load(id: string): Promise<MessageData[] | undefined> {
      return chatHistory[id];
    },
    async save(id: string, history: MessageData[]) {
      chatHistory[id] = history;
    },
  };
}

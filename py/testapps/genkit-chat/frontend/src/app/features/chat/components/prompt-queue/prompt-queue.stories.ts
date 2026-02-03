/**
 * Copyright 2026 Google LLC
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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Meta, StoryObj } from '@storybook/angular';
import { PromptQueueComponent, type QueueItem } from './prompt-queue.component';

/**
 * PromptQueueComponent displays queued prompts with drag-and-drop reordering,
 * inline editing, and queue management actions.
 *
 * ## Features
 * - Expandable/collapsible queue view
 * - Drag-and-drop reordering
 * - Inline editing of queued items
 * - Send now / send all / clear all actions
 * - Item removal
 */
const meta: Meta<PromptQueueComponent> = {
  title: 'Chat/PromptQueue',
  component: PromptQueueComponent,
  tags: ['autodocs'],
  argTypes: {
    queue: {
      description: 'Array of queued prompt items',
      control: 'object',
    },
    send: {
      action: 'send',
      description: 'Emitted when send now is clicked on an item',
    },
    sendAll: {
      action: 'sendAll',
      description: 'Emitted when send all is clicked',
    },
    remove: {
      action: 'remove',
      description: 'Emitted when an item is removed',
    },
    clearAll: {
      action: 'clearAll',
      description: 'Emitted when clear all is clicked',
    },
    update: {
      action: 'update',
      description: 'Emitted when an item is edited',
    },
    reorder: {
      action: 'reorder',
      description: 'Emitted when items are reordered via drag-drop',
    },
  },
};

export default meta;
type Story = StoryObj<PromptQueueComponent>;

// Sample queue items
const sampleQueue: QueueItem[] = [
  { id: '1', content: 'What is machine learning?' },
  { id: '2', content: 'Explain neural networks in simple terms' },
  { id: '3', content: 'How do I train a model?' },
];

/**
 * Default queue with a few items
 */
export const Default: Story = {
  args: {
    queue: sampleQueue,
  },
};

/**
 * Empty queue
 */
export const Empty: Story = {
  args: {
    queue: [],
  },
};

/**
 * Single item in queue
 */
export const SingleItem: Story = {
  args: {
    queue: [{ id: '1', content: 'Tell me a joke' }],
  },
};

/**
 * Long queue with many items
 */
export const LongQueue: Story = {
  args: {
    queue: [
      { id: '1', content: 'What is TypeScript?' },
      { id: '2', content: 'How do I create interfaces?' },
      { id: '3', content: 'Explain generics in TypeScript' },
      { id: '4', content: 'What are decorators?' },
      { id: '5', content: 'How does type inference work?' },
      { id: '6', content: 'What is the difference between type and interface?' },
      { id: '7', content: 'Explain utility types' },
      { id: '8', content: 'How do I use mapped types?' },
    ],
  },
};

/**
 * Queue with long content items
 */
export const LongContent: Story = {
  args: {
    queue: [
      {
        id: '1',
        content:
          'Can you explain the difference between REST and GraphQL APIs, including their pros and cons, and when to use each one?',
      },
      {
        id: '2',
        content:
          'Write a comprehensive guide on setting up a production-ready Node.js application with TypeScript, including testing, linting, and CI/CD configuration',
      },
    ],
  },
};

/**
 * Queue with code snippets
 */
export const WithCodeSnippets: Story = {
  args: {
    queue: [
      { id: '1', content: 'Review this code: function add(a, b) { return a + b; }' },
      { id: '2', content: 'Fix the bug: const arr = [1,2,3]; arr.forEach(i => arr.push(i*2));' },
      {
        id: '3',
        content:
          'Optimize: for(let i=0; i<arr.length; i++) { for(let j=0; j<arr.length; j++) { ... } }',
      },
    ],
  },
};

/**
 * Queue showing unicode/emoji support
 */
export const WithEmoji: Story = {
  args: {
    queue: [
      { id: '1', content: '🚀 How do I deploy to production?' },
      { id: '2', content: '🐛 Help me debug this error' },
      { id: '3', content: '📚 Recommend books on system design' },
      { id: '4', content: '🎨 Design a color palette for my app' },
    ],
  },
};

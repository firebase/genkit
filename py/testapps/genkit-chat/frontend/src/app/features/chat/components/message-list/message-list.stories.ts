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
import { argsToTemplate } from '@storybook/angular';
import type { Message } from '../../../../core/services/chat.service';
import { MessageListComponent } from './message-list.component';

/**
 * MessageListComponent displays chat messages with markdown rendering,
 * message actions (copy, speak, feedback), and loading states.
 *
 * ## Features
 * - User and assistant message styling
 * - Markdown rendering for assistant responses
 * - Action buttons (copy, speak, thumbs up/down)
 * - Loading indicator with typing animation
 * - Error message display
 */
const meta: Meta<MessageListComponent> = {
  title: 'Chat/MessageList',
  component: MessageListComponent,
  tags: ['autodocs'],
  argTypes: {
    messages: {
      description: 'Array of messages to display',
      control: 'object',
    },
    isLoading: {
      description: 'Whether a response is being generated',
      control: 'boolean',
    },
    markdownMode: {
      description: 'Whether to render markdown in assistant responses',
      control: 'boolean',
    },
  },
  render: (args) => ({
    props: args,
    template: `
      <div style="height: 400px; background: var(--surface, #f5f5f5); padding: 16px;">
        <app-message-list ${argsToTemplate(args)} />
      </div>
    `,
  }),
};

export default meta;
type Story = StoryObj<MessageListComponent>;

// Sample messages for stories
const sampleMessages: Message[] = [
  {
    role: 'user',
    content: 'Hello! Can you help me with a coding question?',
    timestamp: new Date(Date.now() - 60000),
  },
  {
    role: 'assistant',
    content:
      "Of course! I'd be happy to help you with your coding question. What would you like to know?",
    timestamp: new Date(Date.now() - 55000),
    model: 'gemini-2.0-flash',
  },
  {
    role: 'user',
    content: 'How do I create a TypeScript interface?',
    timestamp: new Date(Date.now() - 50000),
  },
  {
    role: 'assistant',
    content: `Here's how to create a TypeScript interface:

\`\`\`typescript
interface User {
  id: string;
  name: string;
  email: string;
  age?: number; // Optional property
}
\`\`\`

**Key points:**
- Use the \`interface\` keyword
- Properties can be required or optional (with \`?\`)
- Interfaces are checked at compile time`,
    timestamp: new Date(Date.now() - 45000),
    model: 'gemini-2.0-flash',
  },
];

/**
 * Default state with a typical conversation
 */
export const Default: Story = {
  args: {
    messages: sampleMessages,
    isLoading: false,
    markdownMode: true,
  },
};

/**
 * Empty state - no messages yet
 */
export const Empty: Story = {
  args: {
    messages: [],
    isLoading: false,
    markdownMode: true,
  },
};

/**
 * Loading state while waiting for a response
 */
export const Loading: Story = {
  args: {
    messages: [
      {
        role: 'user',
        content: 'What is the meaning of life?',
        timestamp: new Date(),
      },
    ],
    isLoading: true,
    markdownMode: true,
  },
};

/**
 * Markdown disabled - shows raw text
 */
export const MarkdownDisabled: Story = {
  args: {
    messages: sampleMessages,
    isLoading: false,
    markdownMode: false,
  },
};

/**
 * Error message state
 */
export const WithError: Story = {
  args: {
    messages: [
      {
        role: 'user',
        content: 'Generate something complex',
        timestamp: new Date(Date.now() - 10000),
      },
      {
        role: 'assistant',
        content: 'An error occurred while processing your request.',
        timestamp: new Date(),
        isError: true,
        errorDetails: 'Error: API rate limit exceeded. Please try again in a few minutes.',
      },
    ],
    isLoading: false,
    markdownMode: true,
  },
};

/**
 * Long conversation with many messages
 */
export const LongConversation: Story = {
  args: {
    messages: [
      ...sampleMessages,
      {
        role: 'user',
        content: 'Can you show me a more complex example?',
        timestamp: new Date(Date.now() - 40000),
      },
      {
        role: 'assistant',
        content: `Sure! Here's a more advanced example with generics:

\`\`\`typescript
interface Repository<T> {
  findById(id: string): Promise<T | null>;
  findAll(): Promise<T[]>;
  create(item: Omit<T, 'id'>): Promise<T>;
  update(id: string, item: Partial<T>): Promise<T>;
  delete(id: string): Promise<boolean>;
}
\`\`\`

This pattern is commonly used in data access layers.`,
        timestamp: new Date(Date.now() - 35000),
        model: 'gemini-2.0-flash',
      },
    ],
    isLoading: false,
    markdownMode: true,
  },
};

/**
 * Single user message only
 */
export const SingleUserMessage: Story = {
  args: {
    messages: [
      {
        role: 'user',
        content: 'Hello world!',
        timestamp: new Date(),
      },
    ],
    isLoading: false,
    markdownMode: true,
  },
};

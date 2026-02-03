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
import { ChatInputComponent } from './chat-input.component';

/**
 * ChatInputComponent is the main input area for composing messages.
 * It includes text input, file attachments, voice input, and settings.
 *
 * ## Features
 * - Auto-resizing text area
 * - File attachment with drag-and-drop
 * - Voice input integration
 * - Content safety highlighting
 * - Settings dropdown (streaming, markdown, safety)
 * - Send button with animation
 */
const meta: Meta<ChatInputComponent> = {
  title: 'Chat/ChatInput',
  component: ChatInputComponent,
  tags: ['autodocs'],
  argTypes: {
    placeholder: {
      description: 'Placeholder text for the input',
      control: 'text',
    },
    disabled: {
      description: 'Whether the input is disabled',
      control: 'boolean',
    },
    contentFlagged: {
      description: 'Whether content is flagged as unsafe',
      control: 'boolean',
    },
    flaggedLabels: {
      description: 'Labels of flagged content categories',
      control: 'object',
    },
    streamingEnabled: {
      description: 'Whether streaming is enabled',
      control: 'boolean',
    },
    markdownEnabled: {
      description: 'Whether markdown rendering is enabled',
      control: 'boolean',
    },
    safetyEnabled: {
      description: 'Whether content safety is enabled',
      control: 'boolean',
    },
    isRecording: {
      description: 'Whether voice is currently recording',
      control: 'boolean',
    },
    voiceSupported: {
      description: 'Whether voice input is supported',
      control: 'boolean',
    },
    send: {
      action: 'send',
      description: 'Emitted when a message is sent',
    },
    inputChange: {
      action: 'inputChange',
      description: 'Emitted when input text changes',
    },
    toggleVoice: {
      action: 'toggleVoice',
      description: 'Emitted when voice toggle is clicked',
    },
    toggleStreaming: {
      action: 'toggleStreaming',
      description: 'Emitted when streaming toggle is clicked',
    },
    toggleMarkdown: {
      action: 'toggleMarkdown',
      description: 'Emitted when markdown toggle is clicked',
    },
    toggleSafety: {
      action: 'toggleSafety',
      description: 'Emitted when safety toggle is clicked',
    },
  },
};

export default meta;
type Story = StoryObj<ChatInputComponent>;

/**
 * Default empty state
 */
export const Default: Story = {
  args: {
    placeholder: 'Type a message...',
    disabled: false,
    contentFlagged: false,
    flaggedLabels: [],
    streamingEnabled: true,
    markdownEnabled: true,
    safetyEnabled: true,
    isRecording: false,
    voiceSupported: true,
  },
};

/**
 * Input with custom placeholder
 */
export const CustomPlaceholder: Story = {
  args: {
    ...Default.args,
    placeholder: 'Ask me anything about coding...',
  },
};

/**
 * Voice recording state
 */
export const VoiceRecording: Story = {
  args: {
    ...Default.args,
    isRecording: true,
  },
};

/**
 * Voice not supported (no mic button)
 */
export const VoiceNotSupported: Story = {
  args: {
    ...Default.args,
    voiceSupported: false,
  },
};

/**
 * Content flagged as unsafe
 */
export const ContentFlagged: Story = {
  args: {
    ...Default.args,
    contentFlagged: true,
    flaggedLabels: ['toxicity', 'insult'],
  },
};

/**
 * All settings disabled
 */
export const AllSettingsDisabled: Story = {
  args: {
    ...Default.args,
    streamingEnabled: false,
    markdownEnabled: false,
    safetyEnabled: false,
  },
};

/**
 * Disabled input
 */
export const Disabled: Story = {
  args: {
    ...Default.args,
    disabled: true,
    placeholder: 'Chat is disabled...',
  },
};

/**
 * Minimal configuration (no voice, basic settings)
 */
export const Minimal: Story = {
  args: {
    placeholder: 'Enter your prompt',
    disabled: false,
    contentFlagged: false,
    flaggedLabels: [],
    streamingEnabled: false,
    markdownEnabled: false,
    safetyEnabled: false,
    isRecording: false,
    voiceSupported: false,
  },
};

/**
 * Dark theme preview
 */
export const DarkMode: Story = {
  args: {
    ...Default.args,
  },
  parameters: {
    backgrounds: { default: 'dark' },
  },
};

/**
 * RTL language support
 */
export const RTL: Story = {
  args: {
    ...Default.args,
    placeholder: 'اكتب رسالة...',
  },
  decorators: [
    (story) => ({
      ...story(),
      template: `<div dir="rtl">${story().template}</div>`,
    }),
  ],
};

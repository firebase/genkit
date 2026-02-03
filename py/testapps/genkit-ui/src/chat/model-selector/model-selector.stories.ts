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
import { type Model, ModelSelectorComponent, type Provider } from './model-selector.component';

/**
 * ModelSelectorComponent displays a searchable dropdown for selecting AI models,
 * grouped by provider with recent models section.
 *
 * ## Features
 * - Searchable model list
 * - Models grouped by provider
 * - Recent models section
 * - Current selection display
 */
const meta: Meta<ModelSelectorComponent> = {
	title: 'Chat/ModelSelector',
	component: ModelSelectorComponent,
	tags: ['autodocs'],
	argTypes: {
		selectedModel: {
			description: 'Currently selected model ID',
			control: 'text',
		},
		providers: {
			description: 'List of providers with their models',
			control: 'object',
		},
		recentModels: {
			description: 'Recently used models',
			control: 'object',
		},
		modelSelected: {
			action: 'modelSelected',
			description: 'Emitted when a model is selected',
		},
	},
};

export default meta;
type Story = StoryObj<ModelSelectorComponent>;

// Sample providers
const sampleProviders: Provider[] = [
	{
		id: 'google-genai',
		name: 'Google AI',
		available: true,
		models: [
			{
				id: 'googleai/gemini-2.0-flash',
				name: 'Gemini 2.0 Flash',
				capabilities: ['text', 'vision', 'streaming'],
			},
			{
				id: 'googleai/gemini-2.0-pro',
				name: 'Gemini 2.0 Pro',
				capabilities: ['text', 'vision', 'streaming'],
			},
			{
				id: 'googleai/gemini-1.5-flash',
				name: 'Gemini 1.5 Flash',
				capabilities: ['text', 'vision', 'streaming'],
			},
		],
	},
	{
		id: 'anthropic',
		name: 'Anthropic',
		available: true,
		models: [
			{
				id: 'anthropic/claude-3-sonnet',
				name: 'Claude 3 Sonnet',
				capabilities: ['text', 'streaming'],
			},
			{ id: 'anthropic/claude-3-opus', name: 'Claude 3 Opus', capabilities: ['text', 'streaming'] },
			{
				id: 'anthropic/claude-3-haiku',
				name: 'Claude 3 Haiku',
				capabilities: ['text', 'streaming'],
			},
		],
	},
	{
		id: 'openai',
		name: 'OpenAI',
		available: true,
		models: [
			{ id: 'openai/gpt-4o', name: 'GPT-4o', capabilities: ['text', 'vision', 'streaming'] },
			{ id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', capabilities: ['text', 'streaming'] },
			{ id: 'openai/o1-preview', name: 'o1 Preview', capabilities: ['text', 'reasoning'] },
		],
	},
	{
		id: 'ollama',
		name: 'Ollama (Local)',
		available: true,
		models: [
			{ id: 'ollama/llama3.2', name: 'Llama 3.2', capabilities: ['text', 'streaming'] },
			{ id: 'ollama/mistral', name: 'Mistral', capabilities: ['text', 'streaming'] },
			{ id: 'ollama/codellama', name: 'Code Llama', capabilities: ['text', 'code', 'streaming'] },
		],
	},
];

const recentModels: Model[] = [
	{ id: 'googleai/gemini-2.0-flash', name: 'Gemini 2.0 Flash' },
	{ id: 'anthropic/claude-3-sonnet', name: 'Claude 3 Sonnet' },
];

/**
 * Default state with multiple providers
 */
export const Default: Story = {
	args: {
		selectedModel: 'googleai/gemini-2.0-flash',
		providers: sampleProviders,
		recentModels: recentModels,
	},
};

/**
 * Single provider only
 */
export const SingleProvider: Story = {
	args: {
		selectedModel: 'googleai/gemini-2.0-flash',
		providers: [sampleProviders[0]],
		recentModels: [],
	},
};

/**
 * No recent models
 */
export const NoRecentModels: Story = {
	args: {
		selectedModel: 'googleai/gemini-2.0-flash',
		providers: sampleProviders,
		recentModels: [],
	},
};

/**
 * Ollama local models only
 */
export const LocalModelsOnly: Story = {
	args: {
		selectedModel: 'ollama/llama3.2',
		providers: [
			{
				id: 'ollama',
				name: 'Ollama (Local)',
				available: true,
				models: [
					{ id: 'ollama/llama3.2', name: 'Llama 3.2' },
					{ id: 'ollama/llama3.2:3b', name: 'Llama 3.2 3B' },
					{ id: 'ollama/llama3.2:8b', name: 'Llama 3.2 8B' },
					{ id: 'ollama/mistral', name: 'Mistral 7B' },
					{ id: 'ollama/codellama', name: 'Code Llama' },
					{ id: 'ollama/phi3', name: 'Phi-3' },
					{ id: 'ollama/gemma2', name: 'Gemma 2' },
				],
			},
		],
		recentModels: [],
	},
};

/**
 * Many providers and models
 */
export const ManyModels: Story = {
	args: {
		selectedModel: 'googleai/gemini-2.0-flash',
		providers: [
			...sampleProviders,
			{
				id: 'cohere',
				name: 'Cohere',
				available: true,
				models: [
					{ id: 'cohere/command-r', name: 'Command R' },
					{ id: 'cohere/command-r-plus', name: 'Command R+' },
				],
			},
			{
				id: 'mistral',
				name: 'Mistral AI',
				available: true,
				models: [
					{ id: 'mistral/mistral-large', name: 'Mistral Large' },
					{ id: 'mistral/mistral-medium', name: 'Mistral Medium' },
					{ id: 'mistral/codestral', name: 'Codestral' },
				],
			},
		],
		recentModels: recentModels,
	},
};

/**
 * Long model names
 */
export const LongModelNames: Story = {
	args: {
		selectedModel: 'googleai/gemini-2.0-flash-experimental-0205',
		providers: [
			{
				id: 'google-genai',
				name: 'Google AI Studio',
				available: true,
				models: [
					{
						id: 'googleai/gemini-2.0-flash-experimental-0205',
						name: 'Gemini 2.0 Flash Experimental 0205',
					},
					{ id: 'googleai/gemini-2.0-pro-vision-latest', name: 'Gemini 2.0 Pro Vision Latest' },
					{
						id: 'googleai/gemini-1.5-flash-8b-tuned-custom',
						name: 'Gemini 1.5 Flash 8B Tuned Custom',
					},
				],
			},
		],
		recentModels: [],
	},
};

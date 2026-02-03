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
import {
	type Greeting,
	type QuickAction,
	WelcomeScreenComponent,
} from './welcome-screen.component';

/**
 * WelcomeScreenComponent displays an animated greeting with a typewriter effect
 * and quick action chips for common prompts.
 *
 * ## Features
 * - Animated greeting carousel with typewriter effect
 * - Multi-language support with RTL handling
 * - Quick action chips for common prompts
 * - Customizable greetings and actions
 */
const meta: Meta<WelcomeScreenComponent> = {
	title: 'Chat/WelcomeScreen',
	component: WelcomeScreenComponent,
	tags: ['autodocs'],
	argTypes: {
		greetings: {
			description: 'Array of greetings to cycle through',
			control: 'object',
		},
		quickActions: {
			description: 'Quick action buttons',
			control: 'object',
		},
		actionSelected: {
			action: 'actionSelected',
			description: 'Emitted when a quick action is clicked',
		},
	},
};

export default meta;
type Story = StoryObj<WelcomeScreenComponent>;

// Sample greetings
const defaultGreetings: Greeting[] = [
	{ text: 'Hello', lang: 'English', dir: 'ltr', anim: 'type' },
	{ text: 'Hola', lang: 'Spanish', dir: 'ltr', anim: 'type' },
	{ text: 'Bonjour', lang: 'French', dir: 'ltr', anim: 'type' },
	{ text: '你好', lang: 'Chinese', dir: 'ltr', anim: 'slide' },
	{ text: 'مرحبا', lang: 'Arabic', dir: 'rtl', anim: 'slide' },
	{ text: 'こんにちは', lang: 'Japanese', dir: 'ltr', anim: 'slide' },
];

// Sample quick actions
const defaultQuickActions: QuickAction[] = [
	{
		icon: 'code',
		labelKey: 'Write code',
		prompt: 'Help me write a function that...',
		color: '#4285f4',
	},
	{
		icon: 'edit_note',
		labelKey: 'Summarize text',
		prompt: 'Summarize the following text:',
		color: '#34a853',
	},
	{
		icon: 'lightbulb',
		labelKey: 'Brainstorm ideas',
		prompt: 'Give me ideas for...',
		color: '#fbbc05',
	},
	{
		icon: 'translate',
		labelKey: 'Translate',
		prompt: 'Translate the following to French:',
		color: '#ea4335',
	},
];

/**
 * Default welcome screen with greetings and quick actions
 */
export const Default: Story = {
	args: {
		greetings: defaultGreetings,
		quickActions: defaultQuickActions,
	},
};

/**
 * Single greeting (no carousel)
 */
export const SingleGreeting: Story = {
	args: {
		greetings: [{ text: 'Welcome!', lang: 'English', dir: 'ltr', anim: 'type' }],
		quickActions: defaultQuickActions,
	},
};

/**
 * RTL language greeting (Arabic)
 */
export const RTLGreeting: Story = {
	args: {
		greetings: [{ text: 'مرحبا بك', lang: 'Arabic', dir: 'rtl', anim: 'type' }],
		quickActions: [
			{
				icon: 'code',
				labelKey: 'كتابة الكود',
				prompt: 'ساعدني في كتابة...',
				color: '#4285f4',
			},
			{
				icon: 'translate',
				labelKey: 'ترجمة',
				prompt: 'ترجم التالي...',
				color: '#ea4335',
			},
		],
	},
};

/**
 * No quick actions
 */
export const NoQuickActions: Story = {
	args: {
		greetings: defaultGreetings,
		quickActions: [],
	},
};

/**
 * Many quick actions
 */
export const ManyQuickActions: Story = {
	args: {
		greetings: defaultGreetings,
		quickActions: [
			...defaultQuickActions,
			{
				icon: 'psychology',
				labelKey: 'Explain concept',
				prompt: 'Explain the concept of...',
				color: '#9c27b0',
			},
			{
				icon: 'bug_report',
				labelKey: 'Debug code',
				prompt: 'Help me debug this code:',
				color: '#ff5722',
			},
			{
				icon: 'school',
				labelKey: 'Learn something',
				prompt: 'Teach me about...',
				color: '#00bcd4',
			},
			{
				icon: 'create',
				labelKey: 'Write email',
				prompt: 'Write a professional email about...',
				color: '#607d8b',
			},
		],
	},
};

/**
 * Asian language greetings with slide animation
 */
export const AsianLanguages: Story = {
	args: {
		greetings: [
			{ text: '你好', lang: 'Chinese', dir: 'ltr', anim: 'slide' },
			{ text: 'こんにちは', lang: 'Japanese', dir: 'ltr', anim: 'slide' },
			{ text: '안녕하세요', lang: 'Korean', dir: 'ltr', anim: 'slide' },
			{ text: 'สวัสดี', lang: 'Thai', dir: 'ltr', anim: 'slide' },
		],
		quickActions: defaultQuickActions,
	},
};

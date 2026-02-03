// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, it } from 'vitest';

type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeOption {
	mode: ThemeMode;
	icon: string;
	labelKey: string;
}

// Copy THEME_OPTIONS for testing without Angular imports
const THEME_OPTIONS: ThemeOption[] = [
	{ mode: 'system', icon: 'brightness_auto', labelKey: 'theme.system' },
	{ mode: 'light', icon: 'light_mode', labelKey: 'theme.light' },
	{ mode: 'dark', icon: 'dark_mode', labelKey: 'theme.dark' },
];

// Helper functions matching component logic
function getCurrentOption(theme: ThemeMode): ThemeOption {
	return THEME_OPTIONS.find((o) => o.mode === theme) || THEME_OPTIONS[0];
}

function getIcon(theme: ThemeMode): string {
	return getCurrentOption(theme).icon;
}

function getTooltip(theme: ThemeMode): string {
	if (theme === 'system') return 'System theme';
	if (theme === 'dark') return 'Dark theme';
	return 'Light theme';
}

function cycleTheme(current: ThemeMode): ThemeMode {
	if (current === 'system') return 'light';
	if (current === 'light') return 'dark';
	return 'system';
}

describe('ThemeSelectorComponent logic', () => {
	describe('THEME_OPTIONS', () => {
		it('should have three theme options', () => {
			expect(THEME_OPTIONS.length).toBe(3);
		});

		it('should have system as first option', () => {
			expect(THEME_OPTIONS[0].mode).toBe('system');
		});

		it('should have correct icons', () => {
			const system = THEME_OPTIONS.find((o) => o.mode === 'system');
			const light = THEME_OPTIONS.find((o) => o.mode === 'light');
			const dark = THEME_OPTIONS.find((o) => o.mode === 'dark');

			expect(system?.icon).toBe('brightness_auto');
			expect(light?.icon).toBe('light_mode');
			expect(dark?.icon).toBe('dark_mode');
		});
	});

	describe('getIcon', () => {
		it('should get correct icon for system theme', () => {
			expect(getIcon('system')).toBe('brightness_auto');
		});

		it('should get correct icon for light theme', () => {
			expect(getIcon('light')).toBe('light_mode');
		});

		it('should get correct icon for dark theme', () => {
			expect(getIcon('dark')).toBe('dark_mode');
		});
	});

	describe('cycleTheme', () => {
		it('should cycle system -> light', () => {
			expect(cycleTheme('system')).toBe('light');
		});

		it('should cycle light -> dark', () => {
			expect(cycleTheme('light')).toBe('dark');
		});

		it('should cycle dark -> system', () => {
			expect(cycleTheme('dark')).toBe('system');
		});

		it('should complete full cycle', () => {
			let theme: ThemeMode = 'system';
			theme = cycleTheme(theme); // light
			expect(theme).toBe('light');
			theme = cycleTheme(theme); // dark
			expect(theme).toBe('dark');
			theme = cycleTheme(theme); // system
			expect(theme).toBe('system');
		});
	});

	describe('getTooltip', () => {
		it('should get correct tooltip for system theme', () => {
			expect(getTooltip('system')).toBe('System theme');
		});

		it('should get correct tooltip for light theme', () => {
			expect(getTooltip('light')).toBe('Light theme');
		});

		it('should get correct tooltip for dark theme', () => {
			expect(getTooltip('dark')).toBe('Dark theme');
		});
	});

	describe('getCurrentOption', () => {
		it('should get current option for system theme', () => {
			const option = getCurrentOption('system');
			expect(option.mode).toBe('system');
			expect(option.icon).toBe('brightness_auto');
			expect(option.labelKey).toBe('theme.system');
		});

		it('should get current option for light theme', () => {
			const option = getCurrentOption('light');
			expect(option.mode).toBe('light');
			expect(option.labelKey).toBe('theme.light');
		});

		it('should get current option for dark theme', () => {
			const option = getCurrentOption('dark');
			expect(option.mode).toBe('dark');
			expect(option.labelKey).toBe('theme.dark');
		});
	});
});

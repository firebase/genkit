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

// Test setup for Vitest
import { vi } from 'vitest';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });

// Mock matchMedia
Object.defineProperty(globalThis, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock SpeechRecognition
Object.defineProperty(globalThis, 'SpeechRecognition', {
  writable: true,
  value: undefined,
});
Object.defineProperty(globalThis, 'webkitSpeechRecognition', {
  writable: true,
  value: undefined,
});

// Mock speechSynthesis
const speechSynthesisMock = {
  cancel: vi.fn(),
  speak: vi.fn(),
  getVoices: vi.fn().mockReturnValue([]),
};
Object.defineProperty(globalThis, 'speechSynthesis', {
  writable: true,
  value: speechSynthesisMock,
});

// Mock ResizeObserver
class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
Object.defineProperty(globalThis, 'ResizeObserver', {
  writable: true,
  value: ResizeObserverMock,
});

// Mock document properties
Object.defineProperty(document.documentElement, 'dir', {
  writable: true,
  value: 'ltr',
});
Object.defineProperty(document.documentElement, 'lang', {
  writable: true,
  value: 'en',
});

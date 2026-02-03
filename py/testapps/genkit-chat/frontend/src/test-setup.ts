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

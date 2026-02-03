import { defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        globals: true,
        environment: 'jsdom',
        include: ['src/**/*.{test,spec}.{js,ts}'],
        exclude: ['node_modules', 'dist'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            include: ['src/app/**/*.ts'],
            exclude: [
                'src/app/**/*.spec.ts',
                'src/app/**/*.test.ts',
                'src/app/**/*.stories.ts',
                'src/app/app.config.ts',
                'src/app/app.routes.ts',
                'src/main.ts',
            ],
            // NOTE: Current coverage is ~11%. Target is 80%.
            // Pure logic has been extracted to utils/ with ~95% coverage.
            // Component tests require Angular TestBed integration.
            // See py/testapps/GEMINI.md for testing strategy.
            thresholds: {
                lines: 10,
                functions: 10,
                branches: 10,
                statements: 10,
            },
        },
        setupFiles: ['./src/test-setup.ts'],
    },
});

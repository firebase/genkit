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
                'src/app/app.config.ts',
                'src/app/app.routes.ts',
                'src/main.ts',
            ],
            thresholds: {
                lines: 80,
                functions: 80,
                branches: 80,
                statements: 80,
            },
        },
        setupFiles: ['./src/test-setup.ts'],
    },
});

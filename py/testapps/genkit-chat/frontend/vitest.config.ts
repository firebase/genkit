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

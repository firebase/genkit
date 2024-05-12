/**
 * Copyright 2024 Google LLC
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
 */

export const defaultOptions = {
  format: ['cjs', 'esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  shims: true,
  outDir: 'lib',
  entry: ['src/**/*.ts'],
  bundle: false,
  treeshake: false,
};

export function fromPackageJson(packageJson: {
  exports?: { [key: string]: { import: string } };
}): string[] {
  if (!packageJson.exports) return ['./src/index.ts'];
  const out: string[] = [];
  for (const key in packageJson.exports) {
    if (Object.prototype.hasOwnProperty.call(packageJson.exports, key)) {
      const importFile = packageJson.exports[key].import;
      out.push(importFile.replace('./lib', './src').replace('.mjs', '.ts'));
    }
  }
  return out;
}

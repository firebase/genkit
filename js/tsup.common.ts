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

import { Plugin } from 'esbuild';

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
  esbuildPlugins: [forceEsmExtensionsPlugin()],
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

function forceEsmExtensionsPlugin(): Plugin {
  return {
    name: 'forceEsmExtensionsPlugin',
    setup(build) {
      const isEsm = build.initialOptions.format === 'esm';

      build.onEnd(async (result) => {
        if (result.errors.length > 0) {
          return;
        }

        for (const outputFile of result.outputFiles || []) {
          if (
            !(
              outputFile.path.endsWith('.js') ||
              outputFile.path.endsWith('.mjs')
            )
          ) {
            continue;
          }

          const fileContents = outputFile.text;
          const nextFileContents = modifyRelativeImports(fileContents, isEsm);

          outputFile.contents = Buffer.from(nextFileContents);
        }
      });
    },
  };
}

const CJS_RELATIVE_IMPORT_EXP = /require\(["'](\..+)["']\)(;)?/gm;
const ESM_RELATIVE_IMPORT_EXP = /from ["'](\..+)["'](;)?/gm;

function modifyRelativeImports(contents: string, isEsm: boolean): string {
  const extension = isEsm ? '.mjs' : '.js';
  const importExpression = isEsm
    ? ESM_RELATIVE_IMPORT_EXP
    : CJS_RELATIVE_IMPORT_EXP;

  return contents.replace(
    importExpression,
    (_, importPath, maybeSemicolon = '') => {
      if (importPath.endsWith('.')) {
        return isEsm
          ? `from '${importPath}/index${extension}'${maybeSemicolon}`
          : `require("${importPath}/index${extension}")${maybeSemicolon}`;
      }
      if (importPath.endsWith('/')) {
        return isEsm
          ? `from '${importPath}index${extension}'${maybeSemicolon}`
          : `require("${importPath}index${extension}")${maybeSemicolon}`;
      }

      if (importPath.endsWith(extension)) {
        return isEsm
          ? `from '${importPath}'${maybeSemicolon}`
          : `require("${importPath}")${maybeSemicolon}`;
      }

      return isEsm
        ? `from '${maybeStripExistingExtension(importPath)}${extension}'${maybeSemicolon}`
        : `require("${maybeStripExistingExtension(importPath)}${extension}")${maybeSemicolon}`;
    }
  );
}

function maybeStripExistingExtension(importPath: string) {
  if (importPath.endsWith('.js') || importPath.endsWith('.mjs')) {
    return importPath.substring(0, importPath.lastIndexOf('.'));
  }
  return importPath;
}

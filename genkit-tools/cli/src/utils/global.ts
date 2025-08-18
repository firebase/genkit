/**
 * Copyright 2025 Google LLC
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

export interface PackageManager {
  type: string;
  localInstallCommand: string;
  globalInstallCommand: string;
  localInstallCommandFunc: (name: string, version?: string) => string;
  globalInstallCommandFunc: (name: string, version?: string) => string;
  globalRootCommand: string;
}

export const PACKAGE_MANAGERS: Record<string, PackageManager> = {
  npm: {
    type: 'npm',
    localInstallCommand: 'npm install',
    globalInstallCommand: 'npm install -g',
    localInstallCommandFunc: (name: string, version?: string) =>
      `npm install ${name}${version ? `@${version}` : ''}`,
    globalInstallCommandFunc: (name: string, version?: string) =>
      `npm install -g ${name}${version ? `@${version}` : ''}`,
    globalRootCommand: 'npm root -g',
  },
  pnpm: {
    type: 'pnpm',
    localInstallCommand: 'pnpm install',
    globalInstallCommand: 'pnpm install -g',
    localInstallCommandFunc: (name: string, version?: string) =>
      `pnpm install ${name}${version ? `@${version}` : ''}`,
    globalInstallCommandFunc: (name: string, version?: string) =>
      `pnpm install -g ${name}${version ? `@${version}` : ''}`,
    globalRootCommand: 'pnpm root -g',
  },
  yarn: {
    type: 'yarn',
    localInstallCommand: 'yarn install',
    globalInstallCommand: 'yarn install -g',
    localInstallCommandFunc: (name: string, version?: string) =>
      `yarn install ${name}${version ? `@${version}` : ''}`,
    globalInstallCommandFunc: (name: string, version?: string) =>
      `yarn install -g ${name}${version ? `@${version}` : ''}`,
    globalRootCommand: 'yarn global bin',
  },
};

export const getPackageManager = (name: string) => {
  return PACKAGE_MANAGERS[name] || PACKAGE_MANAGERS.npm;
};

export class UpdateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UpdateError';
  }
}

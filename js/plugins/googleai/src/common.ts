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

import { getClientHeader as defaultGetClientHeader } from 'genkit';
import process from 'process';

export function getApiKeyFromEnvVar(): string | undefined {
  return (
    process.env.GEMINI_API_KEY ||
    process.env.GOOGLE_API_KEY ||
    process.env.GOOGLE_GENAI_API_KEY
  );
}

export function getGenkitClientHeader() {
  if (process.env.MONOSPACE_ENV == 'true') {
    return defaultGetClientHeader() + ' firebase-studio-vm';
  }
  return defaultGetClientHeader();
}

// Type-safe name helpers for GoogleAI plugin
const PROVIDER = 'googleai' as const;
type Provider = typeof PROVIDER;
type Prefixed<ActionName extends string> = `${Provider}/${ActionName}`;
type MaybePrefixed<ActionName extends string> =
  | ActionName
  | Prefixed<ActionName>;

// Runtime + typed helpers
export function removePrefix<ActionName extends string>(
  name: MaybePrefixed<ActionName>
): ActionName {
  return (
    name.startsWith(`${PROVIDER}/`)
      ? (name.slice(PROVIDER.length + 1) as ActionName)
      : name
  ) as ActionName;
}

export function ensurePrefixed<ActionName extends string>(
  name: MaybePrefixed<ActionName>
): Prefixed<ActionName> {
  return (
    name.startsWith(`${PROVIDER}/`)
      ? (name as Prefixed<ActionName>)
      : (`${PROVIDER}/${name}` as Prefixed<ActionName>)
  ) as Prefixed<ActionName>;
}

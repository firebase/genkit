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

// Type-safe name helpers/guards

const PREFIX = 'googleai' as const;

type Prefix = typeof PREFIX;

type Prefixed<
  ActionName extends string,
  PrefixType extends string = Prefix,
> = `${PrefixType}/${ActionName}`;

type MaybePrefixed<
  ActionName extends string,
  PrefixType extends string = Prefix,
> = ActionName | Prefixed<ActionName, PrefixType>;

/**
 * Removes a prefix from an action name if it exists.
 *
 * @template ActionName - The action name type
 * @template PrefixType - The prefix type (defaults to 'googleai')
 *
 * @param name - The action name, which may or may not be prefixed
 * @param prefix - The prefix to remove (defaults to 'googleai')
 *
 * @returns The action name without the prefix
 *
 * @example
 * ```typescript
 * removePrefix('googleai/gemini-1.5-flash') // 'gemini-1.5-flash'
 * removePrefix('gemini-1.5-flash') // 'gemini-1.5-flash'
 * removePrefix('openai/gpt-4', 'openai') // 'gpt-4'
 * ```
 */
export function removePrefix<
  ActionName extends string,
  PrefixType extends string = Prefix,
>(
  name: MaybePrefixed<ActionName, PrefixType>,
  prefix: PrefixType = PREFIX as PrefixType
): ActionName {
  return (
    name.startsWith(`${prefix}/`)
      ? (name.slice(prefix.length + 1) as ActionName)
      : name
  ) as ActionName;
}

/**
 * This function adds the prefix if it's missing, or returns the name unchanged
 * if it already has the correct prefix. This prevents double-prefixing issues.
 *
 * @param name - The action name, which may or may not be prefixed
 * @param prefix - The prefix to ensure (defaults to 'googleai')
 *
 * @returns The action name with the prefix guaranteed to be present
 *
 * @example
 * ```typescript
 * ensurePrefixed('gemini-1.5-flash') // 'googleai/gemini-1.5-flash'
 * ensurePrefixed('googleai/gemini-1.5-flash') // 'googleai/gemini-1.5-flash'
 * ```
 */
export function ensurePrefixed<
  ActionName extends string,
  PrefixType extends string = Prefix,
>(
  name: MaybePrefixed<ActionName, PrefixType>,
  prefix: PrefixType = PREFIX as PrefixType
): Prefixed<ActionName, PrefixType> {
  return (
    name.startsWith(`${prefix}/`)
      ? (name as Prefixed<ActionName, PrefixType>)
      : (`${prefix}/${name}` as Prefixed<ActionName, PrefixType>)
  ) as Prefixed<ActionName, PrefixType>;
}

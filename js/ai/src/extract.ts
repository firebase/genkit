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

import JSON5 from 'json5';

/**
 * Extracts JSON from string with lenient parsing rules to improve likelihood of successful extraction.
 * TEST. DO NOT SUBMIT. 
 */
export function extractJson<T = unknown>(text: string): T | null {
  let openingChar: '{' | '[' | undefined;
  let closingChar: '}' | ']' | undefined;
  let startPos: number | undefined;
  let nestingCount = 0;

  for (let i = 0; i < text.length; i++) {
    const char = text[i].replace(/\u00A0/g, ' ');

    if (!openingChar && (char === '{' || char === '[')) {
      // Look for opening character
      openingChar = char;
      closingChar = char === '{' ? '}' : ']';
      startPos = i;
      nestingCount++;
    } else if (char === openingChar) {
      // Increment nesting for matching opening character
      nestingCount++;
    } else if (char === closingChar) {
      // Decrement nesting for matching closing character
      nestingCount--;
      if (!nestingCount) {
        // Reached end of target element
        return JSON5.parse(text.substring(startPos || 0, i + 1)) as T;
      }
    }
  }

  if (startPos !== undefined && nestingCount > 0) {
    try {
      return JSON5.parse(text.substring(startPos) + (closingChar || '')) as T;
    } catch (e) {
      throw new Error(`Invalid JSON extracted from model output: ${text}`);
    }
  }
  throw new Error(`No JSON object or array found in model output: ${text}`);
}

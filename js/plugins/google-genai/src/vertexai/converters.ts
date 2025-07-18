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

import { z } from 'genkit';
import {
  HarmBlockThreshold,
  HarmCategory,
  SafetySetting,
} from '../common/types';
import { SafetySettingsSchema } from './gemini';

export function toGeminiSafetySettings(
  genkitSettings?: z.infer<typeof SafetySettingsSchema>[]
): SafetySetting[] | undefined {
  if (!genkitSettings) return undefined;
  return genkitSettings.map((s) => {
    return {
      category: s.category as HarmCategory,
      threshold: s.threshold as HarmBlockThreshold,
    };
  });
}

export function toGeminiLabels(
  labels?: Record<string, string>
): Record<string, string> | undefined {
  if (!labels) {
    return undefined;
  }
  const keys = Object.keys(labels);
  const newLabels: Record<string, string> = {};
  for (const key of keys) {
    const value = labels[key];
    if (!key) {
      continue;
    }
    newLabels[key] = value;
  }

  if (Object.keys(newLabels).length == 0) {
    return undefined;
  }
  return newLabels;
}

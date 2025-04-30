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

export class BaseModule {}

export function formatMap(
  templateString: string,
  valueMap: Record<string, unknown>
): string {
  // Use a regular expression to find all placeholders in the template string
  const regex = /\{([^}]+)\}/g;

  // Replace each placeholder with its corresponding value from the valueMap
  return templateString.replace(regex, (match, key) => {
    if (Object.prototype.hasOwnProperty.call(valueMap, key)) {
      const value = valueMap[key];
      // Convert the value to a string if it's not a string already
      return value !== undefined && value !== null ? String(value) : '';
    } else {
      // Handle missing keys
      throw new Error(`Key '${key}' not found in valueMap.`);
    }
  });
}

export function setValueByPath(
  data: Record<string, unknown>,
  keys: string[],
  value: unknown
): void {
  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];

    if (key.endsWith('[]')) {
      const keyName = key.slice(0, -2);
      if (!(keyName in data)) {
        if (Array.isArray(value)) {
          data[keyName] = Array.from({ length: value.length }, () => ({}));
        } else {
          throw new Error(`Value must be a list given an array path ${key}`);
        }
      }

      if (Array.isArray(data[keyName])) {
        const arrayData = data[keyName] as Array<unknown>;

        if (Array.isArray(value)) {
          for (let j = 0; j < arrayData.length; j++) {
            const entry = arrayData[j] as Record<string, unknown>;
            setValueByPath(entry, keys.slice(i + 1), value[j]);
          }
        } else {
          for (const d of arrayData) {
            setValueByPath(
              d as Record<string, unknown>,
              keys.slice(i + 1),
              value
            );
          }
        }
      }
      return;
    } else if (key.endsWith('[0]')) {
      const keyName = key.slice(0, -3);
      if (!(keyName in data)) {
        data[keyName] = [{}];
      }
      const arrayData = (data as Record<string, unknown>)[keyName];
      setValueByPath(
        (arrayData as Array<Record<string, unknown>>)[0],
        keys.slice(i + 1),
        value
      );
      return;
    }

    if (!data[key] || typeof data[key] !== 'object') {
      data[key] = {};
    }

    data = data[key] as Record<string, unknown>;
  }

  const keyToSet = keys[keys.length - 1];
  const existingData = data[keyToSet];

  if (existingData !== undefined) {
    if (
      !value ||
      (typeof value === 'object' && Object.keys(value).length === 0)
    ) {
      return;
    }

    if (value === existingData) {
      return;
    }

    if (
      typeof existingData === 'object' &&
      typeof value === 'object' &&
      existingData !== null &&
      value !== null
    ) {
      Object.assign(existingData, value);
    } else {
      throw new Error(`Cannot set value for an existing key. Key: ${keyToSet}`);
    }
  } else {
    data[keyToSet] = value;
  }
}

export function getValueByPath(data: unknown, keys: string[]): unknown {
  try {
    if (keys.length === 1 && keys[0] === '_self') {
      return data;
    }

    for (let i = 0; i < keys.length; i++) {
      if (typeof data !== 'object' || data === null) {
        return undefined;
      }

      const key = keys[i];
      if (key.endsWith('[]')) {
        const keyName = key.slice(0, -2);
        if (keyName in data) {
          const arrayData = (data as Record<string, unknown>)[keyName];
          if (!Array.isArray(arrayData)) {
            return undefined;
          }
          return arrayData.map((d) => getValueByPath(d, keys.slice(i + 1)));
        } else {
          return undefined;
        }
      } else {
        data = (data as Record<string, unknown>)[key];
      }
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      return undefined;
    }
    throw error;
  }
}

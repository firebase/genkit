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

import {
  EmbedderReference,
  GenkitError,
  JSONSchema,
  MediaPart,
  ModelReference,
  Part,
  z,
} from 'genkit';
import { GenerateRequest } from 'genkit/model';

/**
 * Safely extracts the error message from the error.
 * @param e The error
 * @returns The error message
 */
export function extractErrMsg(e: unknown): string {
  let errorMessage = 'An unknown error occurred';
  if (e instanceof Error) {
    errorMessage = e.message;
  } else if (typeof e === 'string') {
    errorMessage = e;
  } else {
    // Fallback for other types
    try {
      errorMessage = JSON.stringify(e);
    } catch (stringifyError) {
      errorMessage = 'Failed to stringify error object';
    }
  }
  return errorMessage;
}

/**
 * Gets the un-prefixed model name from a modelReference
 */
export function extractVersion(
  model: ModelReference<z.ZodTypeAny> | EmbedderReference<z.ZodTypeAny>
): string {
  return model.version ? model.version : checkModelName(model.name);
}

/**
 * Gets the model name without certain prefixes..
 * e.g. for "models/googleai/gemini-2.5-pro" it returns just 'gemini-2.5-pro'
 * @param name A string containing the model string with possible prefixes
 * @returns the model string stripped of certain prefixes
 */
export function modelName(name?: string): string | undefined {
  if (!name) return name;

  // Remove any of these prefixes:
  const prefixesToRemove =
    /background-model\/|model\/|models\/|embedders\/|googleai\/|vertexai\//g;
  return name.replace(prefixesToRemove, '');
}

/**
 * Gets the suffix of a model string.
 * Throws if the string is empty.
 * @param name A string containing the model string
 * @returns the model string stripped of prefixes and guaranteed not empty.
 */
export function checkModelName(name?: string): string {
  const version = modelName(name);
  if (!version) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'Model name is required.',
    });
  }
  return version;
}

export function extractText(request: GenerateRequest) {
  return (
    request.messages
      .at(-1)
      ?.content.map((c) => c.text || '')
      .join('') ?? ''
  );
}

const KNOWN_MIME_TYPES = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  mp4: 'video/mp4',
  pdf: 'application/pdf',
};

export function extractMimeType(url?: string): string {
  if (!url) {
    return '';
  }

  const dataPrefix = 'data:';
  if (!url.startsWith(dataPrefix)) {
    // Not a data url, try suffix
    url.lastIndexOf('.');
    const key = url.substring(url.lastIndexOf('.') + 1);
    if (Object.keys(KNOWN_MIME_TYPES).includes(key)) {
      return KNOWN_MIME_TYPES[key];
    }
    return '';
  }

  const commaIndex = url.indexOf(',');
  if (commaIndex == -1) {
    // Invalid - missing separator
    return '';
  }

  // The part between 'data:' and the comma
  let mimeType = url.substring(dataPrefix.length, commaIndex);
  const base64Marker = ';base64';
  if (mimeType.endsWith(base64Marker)) {
    mimeType = mimeType.substring(0, mimeType.length - base64Marker.length);
  }

  return mimeType.trim();
}

export function checkSupportedMimeType(
  media: MediaPart['media'],
  supportedTypes: string[]
) {
  if (!supportedTypes.includes(media.contentType ?? '')) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: `Invalid mimeType for ${displayUrl(media.url)}: "${media.contentType}". Supported mimeTypes: ${supportedTypes.join(', ')}`,
    });
  }
}

/**
 *
 * @param url The url to show (e.g. in an error message)
 * @returns The appropriately  sized url
 */
export function displayUrl(url: string): string {
  if (url.length <= 50) {
    return url;
  }

  return url.substring(0, 25) + '...' + url.substring(url.length - 25);
}

/**
 *
 * @param request A generate request to extract from
 * @param metadataType The media must have metadata matching this type if isDefault is false
 * @param isDefault 'true' allows missing metadata type to match as well.
 * @returns
 */
export function extractMedia(
  request: GenerateRequest,
  params: {
    metadataType?: string;
    /* Is there is no metadata type, it will match if isDefault is true */
    isDefault?: boolean;
  }
): MediaPart['media'] | undefined {
  const predicate = (part: Part) => {
    const media = part.media;
    if (!media) {
      return false;
    }
    if (params.metadataType || params.isDefault) {
      // We need to check the metadata type
      const metadata = part.metadata;
      if (!metadata?.type) {
        return !!params.isDefault;
      } else {
        return metadata.type == params.metadataType;
      }
    }
    return true;
  };

  const media = request.messages.at(-1)?.content.find(predicate)?.media;

  // Add the mimeType
  if (media && !media?.contentType) {
    return {
      url: media.url,
      contentType: extractMimeType(media.url),
    };
  }

  return media;
}

/**
 * Cleans a JSON schema by removing specific keys and standardizing types.
 *
 * @param {JSONSchema} schema The JSON schema to clean.
 * @returns {JSONSchema} The cleaned JSON schema.
 */
export function cleanSchema(schema: JSONSchema): JSONSchema {
  const out = structuredClone(schema);
  for (const key in out) {
    if (key === '$schema' || key === 'additionalProperties') {
      delete out[key];
      continue;
    }
    if (typeof out[key] === 'object') {
      out[key] = cleanSchema(out[key]);
    }
    // Zod nullish() and picoschema optional fields will produce type `["string", "null"]`
    // which is not supported by the model API. Convert them to just `"string"`.
    if (key === 'type' && Array.isArray(out[key])) {
      // find the first that's not `null`.
      out[key] = out[key].find((t) => t !== 'null');
    }
  }
  return out;
}

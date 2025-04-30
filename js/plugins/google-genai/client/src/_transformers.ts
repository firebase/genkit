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

import { ApiClient } from './_api_client';
import * as types from './types';

export function tModel(apiClient: ApiClient, model: string | unknown): string {
  if (!model || typeof model !== 'string') {
    throw new Error('model is required and must be a string');
  }

  if (apiClient.isVertexAI()) {
    if (
      model.startsWith('publishers/') ||
      model.startsWith('projects/') ||
      model.startsWith('models/')
    ) {
      return model;
    } else if (model.indexOf('/') >= 0) {
      const parts = model.split('/', 2);
      return `publishers/${parts[0]}/models/${parts[1]}`;
    } else {
      return `publishers/google/models/${model}`;
    }
  } else {
    if (model.startsWith('models/') || model.startsWith('tunedModels/')) {
      return model;
    } else {
      return `models/${model}`;
    }
  }
}

export function tCachesModel(
  apiClient: ApiClient,
  model: string | unknown
): string {
  const transformedModel = tModel(apiClient, model as string);
  if (!transformedModel) {
    return '';
  }

  if (transformedModel.startsWith('publishers/') && apiClient.isVertexAI()) {
    // vertex caches only support model name start with projects.
    return `projects/${apiClient.getProject()}/locations/${apiClient.getLocation()}/${transformedModel}`;
  } else if (transformedModel.startsWith('models/') && apiClient.isVertexAI()) {
    return `projects/${apiClient.getProject()}/locations/${apiClient.getLocation()}/publishers/google/${transformedModel}`;
  } else {
    return transformedModel;
  }
}

export function tBlobs(
  apiClient: ApiClient,
  blobs: types.BlobImageUnion | types.BlobImageUnion[]
): types.Blob[] {
  if (Array.isArray(blobs)) {
    return blobs.map((blob) => tBlob(apiClient, blob));
  } else {
    return [tBlob(apiClient, blobs)];
  }
}

export function tBlob(
  apiClient: ApiClient,
  blob: types.BlobImageUnion
): types.Blob {
  if (typeof blob === 'object' && blob !== null) {
    return blob;
  }

  throw new Error(
    `Could not parse input as Blob. Unsupported blob type: ${typeof blob}`
  );
}

export function tImageBlob(
  apiClient: ApiClient,
  blob: types.BlobImageUnion
): types.Blob {
  const transformedBlob = tBlob(apiClient, blob);
  if (
    transformedBlob.mimeType &&
    transformedBlob.mimeType.startsWith('image/')
  ) {
    return transformedBlob;
  }
  throw new Error(`Unsupported mime type: ${transformedBlob.mimeType!}`);
}

export function tAudioBlob(apiClient: ApiClient, blob: types.Blob): types.Blob {
  const transformedBlob = tBlob(apiClient, blob);
  if (
    transformedBlob.mimeType &&
    transformedBlob.mimeType.startsWith('audio/')
  ) {
    return transformedBlob;
  }
  throw new Error(`Unsupported mime type: ${transformedBlob.mimeType!}`);
}

export function tPart(
  apiClient: ApiClient,
  origin?: types.PartUnion | null
): types.Part {
  if (origin === null || origin === undefined) {
    throw new Error('PartUnion is required');
  }
  if (typeof origin === 'object') {
    return origin;
  }
  if (typeof origin === 'string') {
    return { text: origin };
  }
  throw new Error(`Unsupported part type: ${typeof origin}`);
}

export function tParts(
  apiClient: ApiClient,
  origin?: types.PartListUnion | null
): types.Part[] {
  if (
    origin === null ||
    origin === undefined ||
    (Array.isArray(origin) && origin.length === 0)
  ) {
    throw new Error('PartListUnion is required');
  }
  if (Array.isArray(origin)) {
    return origin.map((item) => tPart(apiClient, item as types.PartUnion)!);
  }
  return [tPart(apiClient, origin)!];
}

function _isContent(origin: unknown): boolean {
  return (
    origin !== null &&
    origin !== undefined &&
    typeof origin === 'object' &&
    'parts' in origin &&
    Array.isArray(origin.parts)
  );
}

function _isFunctionCallPart(origin: unknown): boolean {
  return (
    origin !== null &&
    origin !== undefined &&
    typeof origin === 'object' &&
    'functionCall' in origin
  );
}

function _isFunctionResponsePart(origin: unknown): boolean {
  return (
    origin !== null &&
    origin !== undefined &&
    typeof origin === 'object' &&
    'functionResponse' in origin
  );
}

export function tContent(
  apiClient: ApiClient,
  origin?: types.ContentUnion
): types.Content {
  if (origin === null || origin === undefined) {
    throw new Error('ContentUnion is required');
  }
  if (_isContent(origin)) {
    // _isContent is a utility function that checks if the
    // origin is a Content.
    return origin as types.Content;
  }

  return {
    role: 'user',
    parts: tParts(apiClient, origin as types.PartListUnion)!,
  };
}

export function tContentsForEmbed(
  apiClient: ApiClient,
  origin: types.ContentListUnion
): types.ContentUnion[] {
  if (!origin) {
    return [];
  }
  if (apiClient.isVertexAI() && Array.isArray(origin)) {
    return origin.flatMap((item) => {
      const content = tContent(apiClient, item as types.ContentUnion);
      if (
        content.parts &&
        content.parts.length > 0 &&
        content.parts[0].text !== undefined
      ) {
        return [content.parts[0].text];
      }
      return [];
    });
  } else if (apiClient.isVertexAI()) {
    const content = tContent(apiClient, origin as types.ContentUnion);
    if (
      content.parts &&
      content.parts.length > 0 &&
      content.parts[0].text !== undefined
    ) {
      return [content.parts[0].text];
    }
    return [];
  }
  if (Array.isArray(origin)) {
    return origin.map(
      (item) => tContent(apiClient, item as types.ContentUnion)!
    );
  }
  return [tContent(apiClient, origin as types.ContentUnion)!];
}

export function tContents(
  apiClient: ApiClient,
  origin?: types.ContentListUnion
): types.Content[] {
  if (
    origin === null ||
    origin === undefined ||
    (Array.isArray(origin) && origin.length === 0)
  ) {
    throw new Error('contents are required');
  }
  if (!Array.isArray(origin)) {
    // If it's not an array, it's a single content or a single PartUnion.
    if (_isFunctionCallPart(origin) || _isFunctionResponsePart(origin)) {
      throw new Error(
        'To specify functionCall or functionResponse parts, please wrap them in a Content object, specifying the role for them'
      );
    }
    return [tContent(apiClient, origin as types.ContentUnion)];
  }

  const result: types.Content[] = [];
  const accumulatedParts: types.PartUnion[] = [];
  const isContentArray = _isContent(origin[0]);

  for (const item of origin) {
    const isContent = _isContent(item);

    if (isContent != isContentArray) {
      throw new Error(
        'Mixing Content and Parts is not supported, please group the parts into a the appropriate Content objects and specify the roles for them'
      );
    }

    if (isContent) {
      // `isContent` contains the result of _isContent, which is a utility
      // function that checks if the item is a Content.
      result.push(item as types.Content);
    } else if (_isFunctionCallPart(item) || _isFunctionResponsePart(item)) {
      throw new Error(
        'To specify functionCall or functionResponse parts, please wrap them, and any other parts, in Content objects as appropriate, specifying the role for them'
      );
    } else {
      accumulatedParts.push(item as types.PartUnion);
    }
  }

  if (!isContentArray) {
    result.push({ role: 'user', parts: tParts(apiClient, accumulatedParts) });
  }
  return result;
}

export function tSchema(
  apiClient: ApiClient,
  schema: types.Schema
): types.Schema {
  return schema;
}

export function tSpeechConfig(
  apiClient: ApiClient,
  speechConfig: types.SpeechConfigUnion
): types.SpeechConfig {
  if (typeof speechConfig === 'object') {
    return speechConfig;
  } else if (typeof speechConfig === 'string') {
    return {
      voiceConfig: {
        prebuiltVoiceConfig: {
          voiceName: speechConfig,
        },
      },
    };
  } else {
    throw new Error(`Unsupported speechConfig type: ${typeof speechConfig}`);
  }
}

export function tTool(apiClient: ApiClient, tool: types.Tool): types.Tool {
  return tool;
}

export function tTools(
  apiClient: ApiClient,
  tool: types.Tool[] | unknown
): types.Tool[] {
  if (!Array.isArray(tool)) {
    throw new Error('tool is required and must be an array of Tools');
  }
  return tool;
}

/**
 * Prepends resource name with project, location, resource_prefix if needed.
 *
 * @param client The API client.
 * @param resourceName The resource name.
 * @param resourcePrefix The resource prefix.
 * @param splitsAfterPrefix The number of splits after the prefix.
 * @returns The completed resource name.
 *
 * Examples:
 *
 * ```
 * resource_name = '123'
 * resource_prefix = 'cachedContents'
 * splits_after_prefix = 1
 * client.vertexai = True
 * client.project = 'bar'
 * client.location = 'us-west1'
 * _resource_name(client, resource_name, resource_prefix, splits_after_prefix)
 * returns: 'projects/bar/locations/us-west1/cachedContents/123'
 * ```
 *
 * ```
 * resource_name = 'projects/foo/locations/us-central1/cachedContents/123'
 * resource_prefix = 'cachedContents'
 * splits_after_prefix = 1
 * client.vertexai = True
 * client.project = 'bar'
 * client.location = 'us-west1'
 * _resource_name(client, resource_name, resource_prefix, splits_after_prefix)
 * returns: 'projects/foo/locations/us-central1/cachedContents/123'
 * ```
 *
 * ```
 * resource_name = '123'
 * resource_prefix = 'cachedContents'
 * splits_after_prefix = 1
 * client.vertexai = False
 * _resource_name(client, resource_name, resource_prefix, splits_after_prefix)
 * returns 'cachedContents/123'
 * ```
 *
 * ```
 * resource_name = 'some/wrong/cachedContents/resource/name/123'
 * resource_prefix = 'cachedContents'
 * splits_after_prefix = 1
 * client.vertexai = False
 * # client.vertexai = True
 * _resource_name(client, resource_name, resource_prefix, splits_after_prefix)
 * -> 'some/wrong/resource/name/123'
 * ```
 */
function resourceName(
  client: ApiClient,
  resourceName: string,
  resourcePrefix: string,
  splitsAfterPrefix: number = 1
): string {
  const shouldAppendPrefix =
    !resourceName.startsWith(`${resourcePrefix}/`) &&
    resourceName.split('/').length === splitsAfterPrefix;
  if (client.isVertexAI()) {
    if (resourceName.startsWith('projects/')) {
      return resourceName;
    } else if (resourceName.startsWith('locations/')) {
      return `projects/${client.getProject()}/${resourceName}`;
    } else if (resourceName.startsWith(`${resourcePrefix}/`)) {
      return `projects/${client.getProject()}/locations/${client.getLocation()}/${resourceName}`;
    } else if (shouldAppendPrefix) {
      return `projects/${client.getProject()}/locations/${client.getLocation()}/${resourcePrefix}/${resourceName}`;
    } else {
      return resourceName;
    }
  }
  if (shouldAppendPrefix) {
    return `${resourcePrefix}/${resourceName}`;
  }
  return resourceName;
}

export function tCachedContentName(
  apiClient: ApiClient,
  name: string | unknown
): string {
  if (typeof name !== 'string') {
    throw new Error('name must be a string');
  }
  return resourceName(apiClient, name, 'cachedContents');
}

export function tTuningJobStatus(
  apiClient: ApiClient,
  status: string | unknown
): string {
  switch (status) {
    case 'STATE_UNSPECIFIED':
      return 'JOB_STATE_UNSPECIFIED';
    case 'CREATING':
      return 'JOB_STATE_RUNNING';
    case 'ACTIVE':
      return 'JOB_STATE_SUCCEEDED';
    case 'FAILED':
      return 'JOB_STATE_FAILED';
    default:
      return status as string;
  }
}

export function tBytes(
  apiClient: ApiClient,
  fromImageBytes: string | unknown
): string {
  if (typeof fromImageBytes !== 'string') {
    throw new Error('fromImageBytes must be a string');
  }
  // TODO(b/389133914): Remove dummy bytes converter.
  return fromImageBytes;
}
export function tFileName(
  apiClient: ApiClient,
  fromName: string | unknown
): string {
  if (typeof fromName !== 'string') {
    throw new Error('fromName must be a string');
  }
  // Remove the files/ prefx for MLdev urls to get the actual name of the file.
  if (fromName.startsWith('files/')) {
    return fromName.split('files/')[1];
  }
  return fromName;
}

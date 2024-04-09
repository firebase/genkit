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

import { StreamingCallback } from '@genkit-ai/core';
import { getApps, initializeApp } from 'firebase-admin/app';
import { GoogleAuth } from 'google-auth-library';

// cached `GoogleAuth` client.
let auth: GoogleAuth;
function getAuthClient() {
  // Lazy load GoogleAuth client.
  if (!auth) {
    auth = new GoogleAuth();
  }
  return auth;
}

const streamDelimiter = '\n';

export async function callHttpsFunction(
  functionName: string,
  location: string,
  data: any,
  streamingCallback?: StreamingCallback<any>
) {
  const auth = getAuthClient();
  let funcUrl = await getFunctionUrl(functionName, location);
  if (!funcUrl) {
    throw new Error(`Unable to retrieve uri for function at ${functionName}`);
  }
  const tokenClient = await auth.getIdTokenClient(funcUrl);
  const token = await tokenClient.idTokenProvider.fetchIdToken(funcUrl);

  if (streamingCallback) {
    funcUrl += '?stream=true';
  }

  const res = await fetch(funcUrl, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  if (streamingCallback) {
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const result = await reader.read();
      const decodedValue = decoder.decode(result.value);
      if (decodedValue) {
        buffer += decodedValue;
      }
      // If buffer includes the delimiter that means we are still recieving chunks.
      while (buffer.includes(streamDelimiter)) {
        streamingCallback(
          JSON.parse(buffer.substring(0, buffer.indexOf(streamDelimiter)))
        );
        buffer = buffer.substring(
          buffer.indexOf(streamDelimiter) + streamDelimiter.length
        );
      }
      if (result.done) {
        return buffer;
      }
    }
  }
  const responseText = await res.text();
  return responseText;
}

const functionUrlCache = {} as Record<string, string>;

export async function getFunctionUrl(name, location) {
  if (functionUrlCache[name]) {
    return functionUrlCache[name];
  }
  const auth = getAuthClient();
  const projectId = await auth.getProjectId();
  const url =
    'https://cloudfunctions.googleapis.com/v2beta/' +
    `projects/${projectId}/locations/${location}/functions/${name}`;

  const client = await auth.getClient();
  const res = (await client.request({ url })) as any;
  const uri = res.data?.serviceConfig?.uri;
  if (!uri) {
    throw new Error(`Unable to retrieve uri for function at ${url}`);
  }
  functionUrlCache[name] = uri;
  return uri;
}

/**
 * Extracts error message from the given error object, or if input is not an error then just turn the error into a string.
 */
export function getErrorMessage(e: any): string {
  if (e instanceof Error) {
    return e.message;
  }
  return `${e}`;
}

/**
 * Extracts stack trace from the given error object, or if input is not an error then returns undefined.
 */
export function getErrorStack(e: any): string | undefined {
  if (e instanceof Error) {
    return e.stack;
  }
  return undefined;
}

export function getLocation() {
  return process.env['GCLOUD_LOCATION'] || 'us-central1';
}

export function initializeAppIfNecessary() {
  if (!getApps().length) {
    initializeApp();
  }
}

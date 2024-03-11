import {
  OperationSchema,
  StreamingCallback,
  getLocation,
} from '@google-genkit/common';
import {
  Flow,
  FlowInvokeEnvelopeMessage,
  FlowWrapper,
  StepsFunction,
  flow,
} from '@google-genkit/flow';
import { durableFlow } from '@google-genkit/flow/experimental';
import { getFunctions } from 'firebase-admin/functions';
import { logger } from 'firebase-functions/v2';
import {
  HttpsFunction,
  HttpsOptions,
  onRequest,
} from 'firebase-functions/v2/https';
import {
  TaskQueueFunction,
  TaskQueueOptions,
  onTaskDispatched,
} from 'firebase-functions/v2/tasks';
import { GoogleAuth } from 'google-auth-library';
import * as z from 'zod';

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
  var funcUrl = await getFunctionUrl(functionName, location);
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
    var buffer = '';
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

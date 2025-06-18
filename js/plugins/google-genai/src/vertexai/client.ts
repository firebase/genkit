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

import { GENKIT_CLIENT_HEADER } from 'genkit';
import { GoogleAuth } from 'google-auth-library';
import { extractErrMsg } from '../common/utils';
import {
  CitationMetadata,
  ClientOptions,
  Content,
  EmbedContentRequest,
  EmbedContentResponse,
  GenerateContentCandidate,
  GenerateContentRequest,
  GenerateContentResponse,
  GenerateContentStreamResult,
  GroundingMetadata,
  ImagenPredictRequest,
  ImagenPredictResponse,
  ListModelsResponse,
  Model,
} from './types';

export async function listModels(
  clientOptions: ClientOptions
): Promise<Model[]> {
  const url = getVertexAIUrl({
    includeProjectAndLocation: false,
    resourcePath: 'publishers/google/models',
    clientOptions,
  });
  const fetchOptions: RequestInit = {
    method: 'GET',
    headers: await getHeaders(clientOptions),
  };
  const response = await makeRequest(url, fetchOptions);
  const modelResponse = (await response.json()) as ListModelsResponse;
  return modelResponse.publisherModels;
}

export async function generateContent(
  model: string,
  generateContentRequest: GenerateContentRequest,
  clientOptions: ClientOptions
): Promise<GenerateContentResponse> {
  const url = getVertexAIUrl({
    includeProjectAndLocation: true,
    resourcePath: `publishers/google/models/${model}`,
    resourceMethod: 'generateContent',
    clientOptions,
  });
  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: await getHeaders(clientOptions),
    body: JSON.stringify(generateContentRequest),
  };
  const response = await makeRequest(url, fetchOptions);

  const responseJson = (await response.json()) as GenerateContentResponse;
  return responseJson;
}

export async function generateContentStream(
  model: string,
  generateContentRequest: GenerateContentRequest,
  clientOptions: ClientOptions
): Promise<GenerateContentStreamResult> {
  const url = getVertexAIUrl({
    includeProjectAndLocation: true,
    resourcePath: `publishers/google/models/${model}`,
    resourceMethod: 'streamGenerateContent',
    clientOptions,
  });
  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: await getHeaders(clientOptions),
    body: JSON.stringify(generateContentRequest),
  };
  const response = await makeRequest(url, fetchOptions);
  return processStream(response);
}

export async function embedContent(
  model: string,
  embedContentRequest: EmbedContentRequest,
  clientOptions: ClientOptions
): Promise<EmbedContentResponse> {
  const url = getVertexAIUrl({
    includeProjectAndLocation: true,
    resourcePath: `publishers/google/models/${model}`,
    resourceMethod: 'predict', // embedContent is a Vertex API predict call
    clientOptions,
  });

  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: await getHeaders(clientOptions),
    body: JSON.stringify(embedContentRequest),
  };

  const response = await makeRequest(url, fetchOptions);
  return response.json() as Promise<EmbedContentResponse>;
}

export async function imagenPredict(
  model: string,
  imagenPredictRequest: ImagenPredictRequest,
  clientOptions: ClientOptions
): Promise<ImagenPredictResponse> {
  const url = getVertexAIUrl({
    includeProjectAndLocation: true,
    resourcePath: `publishers/google/models/${model}`,
    resourceMethod: 'predict',
    clientOptions,
  });

  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: await getHeaders(clientOptions),
    body: JSON.stringify(imagenPredictRequest),
  };

  const response = await makeRequest(url, fetchOptions);
  return response.json() as Promise<ImagenPredictResponse>;
}

export function getVertexAIUrl(params: {
  includeProjectAndLocation: boolean; // False for listModels, true for most others
  resourcePath: string;
  resourceMethod?: 'streamGenerateContent' | 'generateContent' | 'predict';
  queryParams?: string;
  clientOptions: ClientOptions;
}): string {
  const DEFAULT_API_VERSION = 'v1beta1';
  const API_BASE_PATH = 'aiplatform.googleapis.com';

  const region = params.clientOptions.location || 'us-central1';
  const basePath = `${region}-${API_BASE_PATH}`;

  let resourcePath = params.resourcePath;
  if (params.includeProjectAndLocation) {
    const parent = `projects/${params.clientOptions.projectId}/locations/${params.clientOptions.location}`;
    resourcePath = `${parent}/${params.resourcePath}`;
  }

  let url = `https://${basePath}/${DEFAULT_API_VERSION}/${resourcePath}`;
  if (params.resourceMethod) {
    url += `:${params.resourceMethod}`;
  }
  if (params.queryParams) {
    url += `?${params.queryParams}`;
  }
  if (params.resourceMethod === 'streamGenerateContent') {
    url += `${params.queryParams ? '&' : '?'}alt=sse`;
  }
  return url;
}

async function getHeaders(clientOptions: ClientOptions): Promise<HeadersInit> {
  const token = await getToken(clientOptions.authClient);
  const headers: HeadersInit = {
    Authorization: `Bearer ${token}`,
    'x-goog-user-project': clientOptions.projectId,
    'Content-Type': 'application/json',
    'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
  };
  return headers;
}

async function getToken(authClient: GoogleAuth): Promise<string> {
  const CREDENTIAL_ERROR_MESSAGE =
    '\nUnable to authenticate your request\
        \nDepending on your run time environment, you can get authentication by\
        \n- if in local instance or cloud shell: `!gcloud auth login`\
        \n- if in Colab:\
        \n    -`from google.colab import auth`\
        \n    -`auth.authenticate_user()`\
        \n- if in service account or other: please follow guidance in https://cloud.google.com/docs/authentication';
  const token = await authClient.getAccessToken().catch((e) => {
    throw new Error(CREDENTIAL_ERROR_MESSAGE, e);
  });
  if (!token) {
    throw new Error(CREDENTIAL_ERROR_MESSAGE);
  }
  return token;
}

async function makeRequest(
  url: string,
  fetchOptions: RequestInit
): Promise<Response> {
  try {
    const response = await fetch(url, fetchOptions);
    if (!response.ok) {
      const json = await response.json();
      throw new Error(
        `Error fetching from ${url}: [${response.status} ${response.statusText}] ${json.error.message}`
      );
    }
    return response;
  } catch (e: unknown) {
    console.error(e);
    throw new Error(`Failed to fetch from ${url}: ${extractErrMsg(e)}`);
  }
}

/**
 * Process a response.body stream from the backend and return an
 * iterator that provides one complete GenerateContentResponse at a time
 * and a promise that resolves with a single aggregated
 * GenerateContentResponse.
 *
 * @param response - Response from a fetch call
 * @ignore
 */
async function processStream(
  response: Response | undefined
): Promise<GenerateContentStreamResult> {
  if (response === undefined) {
    throw new Error('Error processing stream because response === undefined');
  }
  if (!response.body) {
    throw new Error('Error processing stream because response.body not found');
  }
  const inputStream = response.body!.pipeThrough(
    new TextDecoderStream('utf8', { fatal: true })
  );
  const responseStream = getResponseStream(
    inputStream
  ) as ReadableStream<GenerateContentResponse>;
  const [stream1, stream2] = responseStream.tee();
  return Promise.resolve({
    stream: generateResponseSequence(stream1),
    response: getResponsePromise(stream2),
  });
}

async function getResponsePromise(
  stream: ReadableStream<GenerateContentResponse>
): Promise<GenerateContentResponse> {
  const allResponses: GenerateContentResponse[] = [];
  const reader = stream.getReader();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      return aggregateResponses(allResponses);
    }
    allResponses.push(value);
  }
}

async function* generateResponseSequence(
  stream: ReadableStream<GenerateContentResponse>
): AsyncGenerator<GenerateContentResponse> {
  const reader = stream.getReader();
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    yield addMissingIndexAndRole(value);
  }
}

function addMissingIndexAndRole(
  response: GenerateContentResponse
): GenerateContentResponse {
  const generateContentResponse = response as GenerateContentResponse;
  if (
    generateContentResponse.candidates &&
    generateContentResponse.candidates.length > 0
  ) {
    generateContentResponse.candidates.forEach((candidate, index) => {
      if (candidate.index === undefined) {
        generateContentResponse.candidates![index].index = index;
      }

      if (candidate.content === undefined) {
        generateContentResponse.candidates![index].content = {} as Content;
      }

      if (candidate.content.role === undefined) {
        generateContentResponse.candidates![index].content.role = 'model';
      }
    });
  }

  return generateContentResponse;
}

/**
 * Reads a raw stream from the fetch response and join incomplete
 * chunks, returning a new stream that provides a single complete
 * GenerateContentResponse in each iteration.
 * @ignore
 */
function getResponseStream(
  inputStream: ReadableStream<string>
): ReadableStream<unknown> {
  const responseLineRE = /^data: (.*)(?:\n\n|\r\r|\r\n\r\n)/;
  const reader = inputStream.getReader();
  const stream = new ReadableStream<unknown>({
    start(controller) {
      let currentText = '';
      return pump();
      function pump(): Promise<(() => Promise<void>) | undefined> {
        return reader.read().then(({ value, done }) => {
          if (done) {
            if (currentText.trim()) {
              controller.error(
                new Error(
                  `Failed to parse final chunk of stream: ${currentText}`
                )
              );
              return;
            }
            controller.close();
            return;
          }

          currentText += value;
          let match = currentText.match(responseLineRE);
          let parsedResponse: unknown;
          while (match) {
            try {
              parsedResponse = JSON.parse(match[1]);
            } catch (e) {
              controller.error(
                new Error(
                  `Error parsing JSON response from stream chunk: "${match[1]}"`
                )
              );
              return;
            }
            controller.enqueue(parsedResponse);
            currentText = currentText.substring(match[0].length);
            match = currentText.match(responseLineRE);
          }
          return pump();
        });
      }
    },
  });
  return stream;
}

/**
 * Aggregates an array of `GenerateContentResponse`s into a single
 * GenerateContentResponse.
 */
function aggregateResponses(
  responses: GenerateContentResponse[]
): GenerateContentResponse {
  const lastResponse = responses[responses.length - 1];

  if (lastResponse === undefined) {
    throw new Error(
      'Error aggregating stream chunks because the final response in stream chunk is undefined'
    );
  }

  const aggregatedResponse: GenerateContentResponse = {};

  if (lastResponse.promptFeedback) {
    aggregatedResponse.promptFeedback = lastResponse.promptFeedback;
  }
  if (lastResponse.usageMetadata) {
    aggregatedResponse.usageMetadata = lastResponse.usageMetadata;
  }

  for (const response of responses) {
    if (!response.candidates || response.candidates.length === 0) {
      continue;
    }
    for (let i = 0; i < response.candidates.length; i++) {
      if (!aggregatedResponse.candidates) {
        aggregatedResponse.candidates = [];
      }
      if (!aggregatedResponse.candidates[i]) {
        aggregatedResponse.candidates[i] = {
          index: response.candidates[i].index ?? i,
          content: {
            role: response.candidates[i].content?.role ?? 'model',
            parts: [{ text: '' }],
          },
        } as GenerateContentCandidate;
      }
      const citationMetadataAggregated: CitationMetadata | undefined =
        aggregateCitationMetadataForCandidate(
          response.candidates[i],
          aggregatedResponse.candidates[i]
        );
      if (citationMetadataAggregated) {
        aggregatedResponse.candidates[i].citationMetadata =
          citationMetadataAggregated;
      }
      const finishResonOfChunk = response.candidates[i].finishReason;
      if (finishResonOfChunk) {
        aggregatedResponse.candidates[i].finishReason =
          response.candidates[i].finishReason;
      }
      const finishMessageOfChunk = response.candidates[i].finishMessage;
      if (finishMessageOfChunk) {
        aggregatedResponse.candidates[i].finishMessage = finishMessageOfChunk;
      }
      const safetyRatingsOfChunk = response.candidates[i].safetyRatings;
      if (safetyRatingsOfChunk) {
        aggregatedResponse.candidates[i].safetyRatings = safetyRatingsOfChunk;
      }
      if (
        response.candidates[i].content &&
        response.candidates[i].content.parts &&
        response.candidates[i].content.parts.length > 0
      ) {
        const { parts } = aggregatedResponse.candidates[i].content;
        for (const part of response.candidates[i].content.parts) {
          // NOTE: cannot have text and functionCall both in the same part.
          // add functionCall(s) to new parts.
          if (part.text) {
            parts[0].text += part.text;
          }
          if (part.functionCall) {
            parts.push({ functionCall: part.functionCall });
          }
        }
      }
      const groundingMetadataAggregated: GroundingMetadata | undefined =
        aggregateGroundingMetadataForCandidate(
          response.candidates[i],
          aggregatedResponse.candidates[i]
        );
      if (groundingMetadataAggregated) {
        aggregatedResponse.candidates[i].groundingMetadata =
          groundingMetadataAggregated;
      }
    }
  }
  if (aggregatedResponse.candidates?.length) {
    aggregatedResponse.candidates.forEach((candidate) => {
      if (
        candidate.content.parts.length > 1 &&
        candidate.content.parts[0].text === ''
      ) {
        candidate.content.parts.shift(); // remove empty text parameter
      }
    });
  }
  return aggregatedResponse;
}

function aggregateCitationMetadataForCandidate(
  candidateChunk: GenerateContentCandidate,
  aggregatedCandidate: GenerateContentCandidate
): CitationMetadata | undefined {
  if (!candidateChunk.citationMetadata) {
    return;
  }
  const emptyCitationMetadata: CitationMetadata = {
    citations: [],
  };
  const citationMetadataAggregated: CitationMetadata =
    aggregatedCandidate.citationMetadata ?? emptyCitationMetadata;
  const citationMetadataChunk: CitationMetadata =
    candidateChunk.citationMetadata!;
  if (citationMetadataChunk.citations) {
    citationMetadataAggregated.citations =
      citationMetadataAggregated.citations!.concat(
        citationMetadataChunk.citations
      );
  }
  return citationMetadataAggregated;
}

function aggregateGroundingMetadataForCandidate(
  candidateChunk: GenerateContentCandidate,
  aggregatedCandidate: GenerateContentCandidate
): GroundingMetadata | undefined {
  if (!candidateChunk.groundingMetadata) {
    return;
  }
  const emptyGroundingMetadata: GroundingMetadata = {
    webSearchQueries: [],
    retrievalQueries: [],
    groundingChunks: [],
    groundingSupports: [],
  };
  const groundingMetadataAggregated: GroundingMetadata =
    aggregatedCandidate.groundingMetadata ?? emptyGroundingMetadata;
  const groundingMetadataChunk: GroundingMetadata =
    candidateChunk.groundingMetadata!;
  if (groundingMetadataChunk.webSearchQueries) {
    groundingMetadataAggregated.webSearchQueries =
      groundingMetadataAggregated.webSearchQueries!.concat(
        groundingMetadataChunk.webSearchQueries
      );
  }
  if (groundingMetadataChunk.retrievalQueries) {
    groundingMetadataAggregated.retrievalQueries =
      groundingMetadataAggregated.retrievalQueries!.concat(
        groundingMetadataChunk.retrievalQueries
      );
  }
  if (groundingMetadataChunk.groundingChunks) {
    groundingMetadataAggregated.groundingChunks =
      groundingMetadataAggregated.groundingChunks!.concat(
        groundingMetadataChunk.groundingChunks
      );
  }
  if (groundingMetadataChunk.groundingSupports) {
    groundingMetadataAggregated.groundingSupports =
      groundingMetadataAggregated.groundingSupports!.concat(
        groundingMetadataChunk.groundingSupports
      );
  }
  if (groundingMetadataChunk.searchEntryPoint) {
    groundingMetadataAggregated.searchEntryPoint =
      groundingMetadataChunk.searchEntryPoint;
  }
  return groundingMetadataAggregated;
}

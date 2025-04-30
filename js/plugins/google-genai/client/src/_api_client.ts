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

import { Auth } from './_auth';
import * as common from './_common';
import { Uploader } from './_uploader';
import { File, HttpOptions, HttpResponse, UploadFileConfig } from './types';

const CONTENT_TYPE_HEADER = 'Content-Type';
const SERVER_TIMEOUT_HEADER = 'X-Server-Timeout';
const USER_AGENT_HEADER = 'User-Agent';
const GOOGLE_API_CLIENT_HEADER = 'x-goog-api-client';
export const SDK_VERSION = '0.10.0'; // x-release-please-version
const LIBRARY_LABEL = `google-genai-sdk/${SDK_VERSION}`;
const VERTEX_AI_API_DEFAULT_VERSION = 'v1beta1';
const GOOGLE_AI_API_DEFAULT_VERSION = 'v1beta';
const responseLineRE = /^data: (.*)(?:\n\n|\r\r|\r\n\r\n)/;

/**
 * Client errors raised by the GenAI API.
 */
export class ClientError extends Error {
  constructor(message: string, stackTrace?: string) {
    if (stackTrace) {
      super(message, { cause: stackTrace });
    } else {
      super(message, { cause: new Error().stack });
    }
    this.message = message;
    this.name = 'ClientError';
  }
}

/**
 * Server errors raised by the GenAI API.
 */
export class ServerError extends Error {
  constructor(message: string, stackTrace?: string) {
    if (stackTrace) {
      super(message, { cause: stackTrace });
    } else {
      super(message, { cause: new Error().stack });
    }
    this.message = message;
    this.name = 'ServerError';
  }
}

/**
 * Options for initializing the ApiClient. The ApiClient uses the parameters
 * for authentication purposes as well as to infer if SDK should send the
 * request to Vertex AI or Gemini API.
 */
export interface ApiClientInitOptions {
  /**
   * The object used for adding authentication headers to API requests.
   */
  auth: Auth;
  /**
   * The uploader to use for uploading files. This field is required for
   * creating a client, will be set through the Node_client or Web_client.
   */
  uploader: Uploader;
  /**
   * Optional. The Google Cloud project ID for Vertex AI users.
   * It is not the numeric project name.
   * If not provided, SDK will try to resolve it from runtime environment.
   */
  project?: string;
  /**
   * Optional. The Google Cloud project location for Vertex AI users.
   * If not provided, SDK will try to resolve it from runtime environment.
   */
  location?: string;
  /**
   * The API Key. This is required for Gemini API users.
   */
  apiKey?: string;
  /**
   * Optional. Set to true if you intend to call Vertex AI endpoints.
   * If unset, default SDK behavior is to call Gemini API.
   */
  vertexai?: boolean;
  /**
   * Optional. The API version for the endpoint.
   * If unset, SDK will choose a default api version.
   */
  apiVersion?: string;
  /**
   * Optional. A set of customizable configuration for HTTP requests.
   */
  httpOptions?: HttpOptions;
  /**
   * Optional. An extra string to append at the end of the User-Agent header.
   *
   * This can be used to e.g specify the runtime and its version.
   */
  userAgentExtra?: string;
}

/**
 * Represents the necessary information to send a request to an API endpoint.
 * This interface defines the structure for constructing and executing HTTP
 * requests.
 */
export interface HttpRequest {
  /**
   * URL path from the modules, this path is appended to the base API URL to
   * form the complete request URL.
   *
   * If you wish to set full URL, use httpOptions.baseUrl instead. Example to
   * set full URL in the request:
   *
   * const request: HttpRequest = {
   *   path: '',
   *   httpOptions: {
   *     baseUrl: 'https://<custom-full-url>',
   *     apiVersion: '',
   *   },
   *   httpMethod: 'GET',
   * };
   *
   * The result URL will be: https://<custom-full-url>
   *
   */
  path: string;
  /**
   * Optional query parameters to be appended to the request URL.
   */
  queryParams?: Record<string, string>;
  /**
   * Optional request body in json string or Blob format, GET request doesn't
   * need a request body.
   */
  body?: string | Blob;
  /**
   * The HTTP method to be used for the request.
   */
  httpMethod: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  /**
   * Optional set of customizable configuration for HTTP requests.
   */
  httpOptions?: HttpOptions;
  /**
   * Optional abort signal which can be used to cancel the request.
   */
  abortSignal?: AbortSignal;
}

/**
 * The ApiClient class is used to send requests to the Gemini API or Vertex AI
 * endpoints.
 */
export class ApiClient {
  readonly clientOptions: ApiClientInitOptions;

  constructor(opts: ApiClientInitOptions) {
    this.clientOptions = {
      ...opts,
      project: opts.project,
      location: opts.location,
      apiKey: opts.apiKey,
      vertexai: opts.vertexai,
    };

    const initHttpOptions: HttpOptions = {};

    if (this.clientOptions.vertexai) {
      initHttpOptions.apiVersion =
        this.clientOptions.apiVersion ?? VERTEX_AI_API_DEFAULT_VERSION;
      // Assume that proj/api key validation occurs before they are passed in.
      if (this.getProject() || this.getLocation()) {
        initHttpOptions.baseUrl = `https://${this.clientOptions.location}-aiplatform.googleapis.com/`;
        this.clientOptions.apiKey = undefined; // unset API key.
      } else {
        initHttpOptions.baseUrl = `https://aiplatform.googleapis.com/`;
        this.clientOptions.project = undefined; // unset project.
        this.clientOptions.location = undefined; // unset location.
      }
    } else {
      initHttpOptions.apiVersion =
        this.clientOptions.apiVersion ?? GOOGLE_AI_API_DEFAULT_VERSION;
      initHttpOptions.baseUrl = `https://generativelanguage.googleapis.com/`;
    }

    initHttpOptions.headers = this.getDefaultHeaders();

    this.clientOptions.httpOptions = initHttpOptions;

    if (opts.httpOptions) {
      this.clientOptions.httpOptions = this.patchHttpOptions(
        initHttpOptions,
        opts.httpOptions
      );
    }
  }

  isVertexAI(): boolean {
    return this.clientOptions.vertexai ?? false;
  }

  getProject() {
    return this.clientOptions.project;
  }

  getLocation() {
    return this.clientOptions.location;
  }

  getApiVersion() {
    if (
      this.clientOptions.httpOptions &&
      this.clientOptions.httpOptions.apiVersion !== undefined
    ) {
      return this.clientOptions.httpOptions.apiVersion;
    }
    throw new Error('API version is not set.');
  }

  getBaseUrl() {
    if (
      this.clientOptions.httpOptions &&
      this.clientOptions.httpOptions.baseUrl !== undefined
    ) {
      return this.clientOptions.httpOptions.baseUrl;
    }
    throw new Error('Base URL is not set.');
  }

  getRequestUrl() {
    return this.getRequestUrlInternal(this.clientOptions.httpOptions);
  }

  getHeaders() {
    if (
      this.clientOptions.httpOptions &&
      this.clientOptions.httpOptions.headers !== undefined
    ) {
      return this.clientOptions.httpOptions.headers;
    } else {
      throw new Error('Headers are not set.');
    }
  }

  private getRequestUrlInternal(httpOptions?: HttpOptions) {
    if (
      !httpOptions ||
      httpOptions.baseUrl === undefined ||
      httpOptions.apiVersion === undefined
    ) {
      throw new Error('HTTP options are not correctly set.');
    }
    const baseUrl = httpOptions.baseUrl.endsWith('/')
      ? httpOptions.baseUrl.slice(0, -1)
      : httpOptions.baseUrl;
    const urlElement: Array<string> = [baseUrl];
    if (httpOptions.apiVersion && httpOptions.apiVersion !== '') {
      urlElement.push(httpOptions.apiVersion);
    }
    return urlElement.join('/');
  }

  getBaseResourcePath() {
    return `projects/${this.clientOptions.project}/locations/${this.clientOptions.location}`;
  }

  getApiKey() {
    return this.clientOptions.apiKey;
  }

  getWebsocketBaseUrl() {
    const baseUrl = this.getBaseUrl();
    const urlParts = new URL(baseUrl);
    urlParts.protocol = urlParts.protocol == 'http:' ? 'ws' : 'wss';
    return urlParts.toString();
  }

  setBaseUrl(url: string) {
    if (this.clientOptions.httpOptions) {
      this.clientOptions.httpOptions.baseUrl = url;
    } else {
      throw new Error('HTTP options are not correctly set.');
    }
  }

  private constructUrl(
    path: string,
    httpOptions: HttpOptions,
    prependProjectLocation: boolean
  ): URL {
    const urlElement: Array<string> = [this.getRequestUrlInternal(httpOptions)];
    if (prependProjectLocation) {
      urlElement.push(this.getBaseResourcePath());
    }
    if (path !== '') {
      urlElement.push(path);
    }
    const url = new URL(`${urlElement.join('/')}`);

    return url;
  }

  private shouldPrependVertexProjectPath(request: HttpRequest): boolean {
    if (this.clientOptions.apiKey) {
      return false;
    }
    if (!this.clientOptions.vertexai) {
      return false;
    }
    if (request.path.startsWith('projects/')) {
      // Assume the path already starts with
      // `projects/<project>/location/<location>`.
      return false;
    }
    if (
      request.httpMethod === 'GET' &&
      request.path.startsWith('publishers/google/models')
    ) {
      // These paths are used by Vertex's models.get and models.list
      // calls. For base models Vertex does not accept a project/location
      // prefix (for tuned model the prefix is required).
      return false;
    }
    return true;
  }

  async request(request: HttpRequest): Promise<HttpResponse> {
    let patchedHttpOptions = this.clientOptions.httpOptions!;
    if (request.httpOptions) {
      patchedHttpOptions = this.patchHttpOptions(
        this.clientOptions.httpOptions!,
        request.httpOptions
      );
    }

    const prependProjectLocation = this.shouldPrependVertexProjectPath(request);
    const url = this.constructUrl(
      request.path,
      patchedHttpOptions,
      prependProjectLocation
    );
    if (request.queryParams) {
      for (const [key, value] of Object.entries(request.queryParams)) {
        url.searchParams.append(key, String(value));
      }
    }
    let requestInit: RequestInit = {};
    if (request.httpMethod === 'GET') {
      if (request.body && request.body !== '{}') {
        throw new Error(
          'Request body should be empty for GET request, but got non empty request body'
        );
      }
    } else {
      requestInit.body = request.body;
    }
    requestInit = await this.includeExtraHttpOptionsToRequestInit(
      requestInit,
      patchedHttpOptions,
      request.abortSignal
    );
    return this.unaryApiCall(url, requestInit, request.httpMethod);
  }

  private patchHttpOptions(
    baseHttpOptions: HttpOptions,
    requestHttpOptions: HttpOptions
  ): HttpOptions {
    const patchedHttpOptions = JSON.parse(
      JSON.stringify(baseHttpOptions)
    ) as HttpOptions;

    for (const [key, value] of Object.entries(requestHttpOptions)) {
      // Records compile to objects.
      if (typeof value === 'object') {
        patchedHttpOptions[key] = { ...patchedHttpOptions[key], ...value };
      } else if (value !== undefined) {
        patchedHttpOptions[key] = value;
      }
    }
    return patchedHttpOptions;
  }

  async requestStream(
    request: HttpRequest
  ): Promise<AsyncGenerator<HttpResponse>> {
    let patchedHttpOptions = this.clientOptions.httpOptions!;
    if (request.httpOptions) {
      patchedHttpOptions = this.patchHttpOptions(
        this.clientOptions.httpOptions!,
        request.httpOptions
      );
    }

    const prependProjectLocation = this.shouldPrependVertexProjectPath(request);
    const url = this.constructUrl(
      request.path,
      patchedHttpOptions,
      prependProjectLocation
    );
    if (!url.searchParams.has('alt') || url.searchParams.get('alt') !== 'sse') {
      url.searchParams.set('alt', 'sse');
    }
    let requestInit: RequestInit = {};
    requestInit.body = request.body;
    requestInit = await this.includeExtraHttpOptionsToRequestInit(
      requestInit,
      patchedHttpOptions,
      request.abortSignal
    );
    return this.streamApiCall(url, requestInit, request.httpMethod);
  }

  private async includeExtraHttpOptionsToRequestInit(
    requestInit: RequestInit,
    httpOptions: HttpOptions,
    abortSignal?: AbortSignal
  ): Promise<RequestInit> {
    if ((httpOptions && httpOptions.timeout) || abortSignal) {
      const abortController = new AbortController();
      const signal = abortController.signal;
      if (httpOptions.timeout && httpOptions?.timeout > 0) {
        setTimeout(() => abortController.abort(), httpOptions.timeout);
      }
      if (abortSignal) {
        abortSignal.addEventListener('abort', () => {
          abortController.abort();
        });
      }
      requestInit.signal = signal;
    }
    requestInit.headers = await this.getHeadersInternal(httpOptions);
    return requestInit;
  }

  private async unaryApiCall(
    url: URL,
    requestInit: RequestInit,
    httpMethod: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  ): Promise<HttpResponse> {
    return this.apiCall(url.toString(), {
      ...requestInit,
      method: httpMethod,
    })
      .then(async (response) => {
        await throwErrorIfNotOK(response);
        return new HttpResponse(response);
      })
      .catch((e) => {
        if (e instanceof Error) {
          throw e;
        } else {
          throw new Error(JSON.stringify(e));
        }
      });
  }

  private async streamApiCall(
    url: URL,
    requestInit: RequestInit,
    httpMethod: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  ): Promise<AsyncGenerator<HttpResponse>> {
    return this.apiCall(url.toString(), {
      ...requestInit,
      method: httpMethod,
    })
      .then(async (response) => {
        await throwErrorIfNotOK(response);
        return this.processStreamResponse(response);
      })
      .catch((e) => {
        if (e instanceof Error) {
          throw e;
        } else {
          throw new Error(JSON.stringify(e));
        }
      });
  }

  async *processStreamResponse(
    response: Response
  ): AsyncGenerator<HttpResponse> {
    const reader = response?.body?.getReader();
    const decoder = new TextDecoder('utf-8');
    if (!reader) {
      throw new Error('Response body is empty');
    }

    try {
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (buffer.trim().length > 0) {
            throw new Error('Incomplete JSON segment at the end');
          }
          break;
        }
        const chunkString = decoder.decode(value);

        // Parse and throw an error if the chunk contains an error.
        try {
          const chunkJson = JSON.parse(chunkString) as Record<string, unknown>;
          if ('error' in chunkJson) {
            const errorJson = JSON.parse(
              JSON.stringify(chunkJson['error'])
            ) as Record<string, unknown>;
            const status = errorJson['status'] as string;
            const code = errorJson['code'] as number;
            const errorMessage = `got status: ${status}. ${JSON.stringify(
              chunkJson
            )}`;
            if (code >= 400 && code < 500) {
              const clientError = new ClientError(errorMessage);
              throw clientError;
            } else if (code >= 500 && code < 600) {
              const serverError = new ServerError(errorMessage);
              throw serverError;
            }
          }
        } catch (e: unknown) {
          const error = e as Error;
          if (error.name === 'ClientError' || error.name === 'ServerError') {
            throw e;
          }
        }
        buffer += chunkString;
        let match = buffer.match(responseLineRE);
        while (match) {
          const processedChunkString = match[1];
          try {
            const partialResponse = new Response(processedChunkString, {
              headers: response?.headers,
              status: response?.status,
              statusText: response?.statusText,
            });
            yield new HttpResponse(partialResponse);
            buffer = buffer.slice(match[0].length);
            match = buffer.match(responseLineRE);
          } catch (e) {
            throw new Error(
              `exception parsing stream chunk ${processedChunkString}. ${e}`
            );
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
  private async apiCall(
    url: string,
    requestInit: RequestInit
  ): Promise<Response> {
    return fetch(url, requestInit).catch((e) => {
      throw new Error(`exception ${e} sending request`);
    });
  }

  getDefaultHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};

    const versionHeaderValue =
      LIBRARY_LABEL + ' ' + this.clientOptions.userAgentExtra;

    headers[USER_AGENT_HEADER] = versionHeaderValue;
    headers[GOOGLE_API_CLIENT_HEADER] = versionHeaderValue;
    headers[CONTENT_TYPE_HEADER] = 'application/json';

    return headers;
  }

  private async getHeadersInternal(
    httpOptions: HttpOptions | undefined
  ): Promise<Headers> {
    const headers = new Headers();
    if (httpOptions && httpOptions.headers) {
      for (const [key, value] of Object.entries(httpOptions.headers)) {
        headers.append(key, value);
      }
      // Append a timeout header if it is set, note that the timeout option is
      // in milliseconds but the header is in seconds.
      if (httpOptions.timeout && httpOptions.timeout > 0) {
        headers.append(
          SERVER_TIMEOUT_HEADER,
          String(Math.ceil(httpOptions.timeout / 1000))
        );
      }
    }
    await this.clientOptions.auth.addAuthHeaders(headers);
    return headers;
  }

  /**
   * Uploads a file asynchronously using Gemini API only, this is not supported
   * in Vertex AI.
   *
   * @param file The string path to the file to be uploaded or a Blob object.
   * @param config Optional parameters specified in the `UploadFileConfig`
   *     interface. @see {@link UploadFileConfig}
   * @return A promise that resolves to a `File` object.
   * @throws An error if called on a Vertex AI client.
   * @throws An error if the `mimeType` is not provided and can not be inferred,
   */
  async uploadFile(
    file: string | Blob,
    config?: UploadFileConfig
  ): Promise<File> {
    const fileToUpload: File = {};
    if (config != null) {
      fileToUpload.mimeType = config.mimeType;
      fileToUpload.name = config.name;
      fileToUpload.displayName = config.displayName;
    }

    if (fileToUpload.name && !fileToUpload.name.startsWith('files/')) {
      fileToUpload.name = `files/${fileToUpload.name}`;
    }

    const uploader = this.clientOptions.uploader;
    const fileStat = await uploader.stat(file);
    fileToUpload.sizeBytes = String(fileStat.size);
    const mimeType = config?.mimeType ?? fileStat.type;
    if (mimeType === undefined || mimeType === '') {
      throw new Error(
        'Can not determine mimeType. Please provide mimeType in the config.'
      );
    }
    fileToUpload.mimeType = mimeType;

    const uploadUrl = await this.fetchUploadUrl(fileToUpload, config);
    return uploader.upload(file, uploadUrl, this);
  }

  private async fetchUploadUrl(
    file: File,
    config?: UploadFileConfig
  ): Promise<string> {
    let httpOptions: HttpOptions = {};
    if (config?.httpOptions) {
      httpOptions = config.httpOptions;
    } else {
      httpOptions = {
        apiVersion: '', // api-version is set in the path.
        headers: {
          'Content-Type': 'application/json',
          'X-Goog-Upload-Protocol': 'resumable',
          'X-Goog-Upload-Command': 'start',
          'X-Goog-Upload-Header-Content-Length': `${file.sizeBytes}`,
          'X-Goog-Upload-Header-Content-Type': `${file.mimeType}`,
        },
      };
    }

    const body: Record<string, File> = {
      file: file,
    };
    const httpResponse = await this.request({
      path: common.formatMap(
        'upload/v1beta/files',
        body['_url'] as Record<string, unknown>
      ),
      body: JSON.stringify(body),
      httpMethod: 'POST',
      httpOptions,
    });

    if (!httpResponse || !httpResponse?.headers) {
      throw new Error(
        'Server did not return an HttpResponse or the returned HttpResponse did not have headers.'
      );
    }

    const uploadUrl: string | undefined =
      httpResponse?.headers?.['x-goog-upload-url'];
    if (uploadUrl === undefined) {
      throw new Error(
        'Failed to get upload url. Server did not return the x-google-upload-url in the headers'
      );
    }
    return uploadUrl;
  }
}

async function throwErrorIfNotOK(response: Response | undefined) {
  if (response === undefined) {
    throw new ServerError('response is undefined');
  }
  if (!response.ok) {
    const status: number = response.status;
    const statusText: string = response.statusText;
    let errorBody: Record<string, unknown>;
    if (response.headers.get('content-type')?.includes('application/json')) {
      errorBody = await response.json();
    } else {
      errorBody = {
        error: {
          message: await response.text(),
          code: response.status,
          status: response.statusText,
        },
      };
    }
    const errorMessage = `got status: ${status} ${statusText}. ${JSON.stringify(
      errorBody
    )}`;
    if (status >= 400 && status < 500) {
      const clientError = new ClientError(errorMessage);
      throw clientError;
    } else if (status >= 500 && status < 600) {
      const serverError = new ServerError(errorMessage);
      throw serverError;
    }
    throw new Error(errorMessage);
  }
}

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

import WebSocket from 'ws';
import { StatusCodes, type Status } from './action.js';
import { Channel } from './async.js';
import { GENKIT_REFLECTION_API_SPEC_VERSION, GENKIT_VERSION } from './index.js';
import { logger } from './logging.js';
import type { Registry } from './registry.js';
import { toJsonSchema } from './schema.js';
import { flushTracing, setTelemetryServerUrl } from './tracing.js';

let apiIndex = 0;

interface JsonRpcRequest {
  jsonrpc: '2.0';
  method: string;
  params?: any;
  id?: number | string;
}

interface JsonRpcResponse {
  jsonrpc: '2.0';
  result?: any;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
  id: number | string;
}

type JsonRpcMessage = JsonRpcRequest | JsonRpcResponse;

export interface ReflectionServerV2Options {
  configuredEnvs?: string[];
  name?: string;
  url: string;
}

export class ReflectionServerV2 {
  private registry: Registry;
  private options: ReflectionServerV2Options;
  private ws: WebSocket | null = null;
  private url: string;
  private index = apiIndex++;
  private activeActions = new Map<
    string,
    {
      abortController: AbortController;
      startTime: Date;
    }
  >();
  private activeRequests = new Map<number | string, Channel<any>>();

  constructor(registry: Registry, options: ReflectionServerV2Options) {
    this.registry = registry;
    this.options = {
      configuredEnvs: ['dev'],
      ...options,
    };
    // The URL should be provided via environment variable by the CLI manager
    this.url = this.options.url;
  }

  async start() {
    logger.debug(`Connecting to Reflection V2 server at ${this.url}`);
    this.ws = new WebSocket(this.url);

    this.ws.on('open', () => {
      logger.debug('Connected to Reflection V2 server.');
      this.register();
    });

    this.ws.on('message', async (data) => {
      try {
        const message = JSON.parse(data.toString()) as JsonRpcMessage;
        if ('method' in message) {
          await this.handleRequest(message as JsonRpcRequest);
        }
      } catch (error) {
        logger.error(`Failed to parse message: ${error}`);
      }
    });

    this.ws.on('error', (error) => {
      logger.error(`Reflection V2 WebSocket error: ${error}`);
    });

    this.ws.on('close', () => {
      logger.debug('Reflection V2 WebSocket closed.');
    });
  }

  async stop() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private send(message: JsonRpcMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private sendResponse(id: number | string, result: any) {
    this.send({
      jsonrpc: '2.0',
      result,
      id,
    });
  }

  private sendError(
    id: number | string,
    code: number,
    message: string,
    data?: any
  ) {
    this.send({
      jsonrpc: '2.0',
      error: { code, message, data },
      id,
    });
  }

  private sendNotification(method: string, params: any) {
    this.send({
      jsonrpc: '2.0',
      method,
      params,
    });
  }

  private register() {
    const params = {
      id: process.env.GENKIT_RUNTIME_ID || this.runtimeId,
      pid: process.pid,
      name: this.options.name || this.runtimeId,
      genkitVersion: GENKIT_VERSION,
      reflectionApiSpecVersion: GENKIT_REFLECTION_API_SPEC_VERSION,
      envs: this.options.configuredEnvs,
    };
    this.sendNotification('register', params);
  }

  get runtimeId() {
    return `${process.pid}${this.index ? `-${this.index}` : ''}`;
  }

  private async handleRequest(request: JsonRpcRequest) {
    try {
      switch (request.method) {
        case 'listActions':
          await this.handleListActions(request);
          break;
        case 'listValues':
          await this.handleListValues(request);
          break;
        case 'runAction':
          await this.handleRunAction(request);
          break;
        case 'configure':
          this.handleConfigure(request);
          break;
        case 'cancelAction':
          await this.handleCancelAction(request);
          break;
        case 'streamInputChunk':
          this.handleStreamInputChunk(request);
          break;
        case 'endStreamInput':
          this.handleEndStreamInput(request);
          break;
        default:
          if (request.id) {
            this.sendError(
              request.id,
              -32601,
              `Method not found: ${request.method}`
            );
          }
      }
    } catch (error: any) {
      if (request.id) {
        this.sendError(request.id, -32000, error.message, {
          stack: error.stack,
        });
      }
    }
  }

  private async handleListActions(request: JsonRpcRequest) {
    if (!request.id) return; // Should be a request
    const actions = await this.registry.listResolvableActions();
    const convertedActions: Record<string, any> = {};

    Object.keys(actions).forEach((key) => {
      const action = actions[key];
      convertedActions[key] = {
        key,
        name: action.name,
        description: action.description,
        metadata: action.metadata,
      };
      if (action.inputSchema || action.inputJsonSchema) {
        convertedActions[key].inputSchema = toJsonSchema({
          schema: action.inputSchema,
          jsonSchema: action.inputJsonSchema,
        });
      }
      if (action.outputSchema || action.outputJsonSchema) {
        convertedActions[key].outputSchema = toJsonSchema({
          schema: action.outputSchema,
          jsonSchema: action.outputJsonSchema,
        });
      }
    });

    this.sendResponse(request.id, convertedActions);
  }

  private async handleListValues(request: JsonRpcRequest) {
    if (!request.id) return;
    const { type } = request.params;
    const values = await this.registry.listValues(type);
    this.sendResponse(request.id, values);
  }

  private async handleRunAction(request: JsonRpcRequest) {
    if (!request.id) return;

    const { key, input, context, telemetryLabels, stream, streamInput } =
      request.params;
    const action = await this.registry.lookupAction(key);

    if (!action) {
      this.sendError(request.id, 404, `action ${key} not found`);
      return;
    }

    const abortController = new AbortController();
    let traceId: string | undefined;
    let inputStream: Channel<any> | undefined;

    // Set up input stream for bidi actions
    if (action.__action.metadata?.bidi) {
      inputStream = new Channel<any>();
      this.activeRequests.set(request.id, inputStream);

      // If initial input is provided, send it
      if (input !== undefined) {
        inputStream.send(input);
      }

      // If input streaming is not requested, close the stream immediately
      // effectively treating initial input as the only input.
      if (!streamInput) {
        inputStream.close();
      }
    }

    try {
      const onTraceStartCallback = ({ traceId: tid }: { traceId: string }) => {
        traceId = tid;
        this.activeActions.set(tid, {
          abortController,
          startTime: new Date(),
        });
        // Send early trace ID notification
        this.sendNotification('runActionState', {
          requestId: request.id,
          state: { traceId: tid },
        });
      };

      if (stream) {
        const callback = (chunk: any) => {
          this.sendNotification('streamChunk', {
            requestId: request.id,
            chunk,
          });
        };

        const result = await action.run(input, {
          context,
          onChunk: callback,
          telemetryLabels,
          onTraceStart: onTraceStartCallback,
          abortSignal: abortController.signal,
          inputStream,
        });

        await flushTracing();

        // Send final result
        this.sendResponse(request.id, {
          result: result.result,
          telemetry: {
            traceId: result.telemetry.traceId,
          },
        });
      } else {
        const result = await action.run(input, {
          context,
          telemetryLabels,
          onTraceStart: onTraceStartCallback,
          abortSignal: abortController.signal,
          inputStream,
        });
        await flushTracing();

        this.sendResponse(request.id, {
          result: result.result,
          telemetry: {
            traceId: result.telemetry.traceId,
          },
        });
      }
    } catch (err: any) {
      const isAbort =
        err?.name === 'AbortError' ||
        (typeof DOMException !== 'undefined' &&
          err instanceof DOMException &&
          err.name === 'AbortError');

      const errorResponse: Status = {
        code: isAbort ? StatusCodes.CANCELLED : StatusCodes.INTERNAL,
        message: isAbort ? 'Action was cancelled' : err.message,
        details: {
          stack: err.stack,
        },
      };
      if (err.traceId || traceId) {
        errorResponse.details.traceId = err.traceId || traceId;
      }

      this.sendError(request.id, -32000, errorResponse.message, errorResponse);
    } finally {
      if (traceId) {
        this.activeActions.delete(traceId);
      }
      if (request.id) {
        this.activeRequests.delete(request.id);
      }
    }
  }

  private handleConfigure(request: JsonRpcRequest) {
    const { telemetryServerUrl } = request.params;
    if (telemetryServerUrl && !process.env.GENKIT_TELEMETRY_SERVER) {
      setTelemetryServerUrl(telemetryServerUrl);
      logger.debug(`Connected to telemetry server on ${telemetryServerUrl}`);
    }
  }

  private async handleCancelAction(request: JsonRpcRequest) {
    if (!request.id) return;
    const { traceId } = request.params;
    if (!traceId || typeof traceId !== 'string') {
      this.sendError(request.id, 400, 'traceId is required');
      return;
    }
    const activeAction = this.activeActions.get(traceId);
    if (activeAction) {
      activeAction.abortController.abort();
      this.activeActions.delete(traceId);
      this.sendResponse(request.id, { message: 'Action cancelled' });
    } else {
      this.sendError(request.id, 404, 'Action not found or already completed');
    }
  }

  private handleStreamInputChunk(request: JsonRpcRequest) {
    const { requestId, chunk } = request.params;
    const channel = this.activeRequests.get(requestId);
    if (channel) {
      channel.send(chunk);
    } else {
      logger.warn(`Received input chunk for unknown request ${requestId}`);
    }
  }

  private handleEndStreamInput(request: JsonRpcRequest) {
    const { requestId } = request.params;
    const channel = this.activeRequests.get(requestId);
    if (channel) {
      channel.close();
    } else {
      logger.warn(`Received end stream input for unknown request ${requestId}`);
    }
  }
}

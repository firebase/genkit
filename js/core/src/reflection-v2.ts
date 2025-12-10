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
        case 'runAction':
          await this.handleRunAction(request);
          break;
        case 'configure':
          this.handleConfigure(request);
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

  private async handleRunAction(request: JsonRpcRequest) {
    if (!request.id) return;

    const { key, input, context, telemetryLabels, stream } = request.params;
    const action = await this.registry.lookupAction(key);

    if (!action) {
      this.sendError(request.id, 404, `action ${key} not found`);
      return;
    }

    try {
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
        const result = await action.run(input, { context, telemetryLabels });
        await flushTracing();

        this.sendResponse(request.id, {
          result: result.result,
          telemetry: {
            traceId: result.telemetry.traceId,
          },
        });
      }
    } catch (err: any) {
      const errorResponse: Status = {
        code: StatusCodes.INTERNAL,
        message: err.message,
        details: {
          stack: err.stack,
        },
      };
      if (err.traceId) {
        errorResponse.details.traceId = err.traceId;
      }

      this.sendError(request.id, -32000, err.message, errorResponse);
    }
  }

  private handleConfigure(request: JsonRpcRequest) {
    const { telemetryServerUrl } = request.params;
    if (telemetryServerUrl && !process.env.GENKIT_TELEMETRY_SERVER) {
      setTelemetryServerUrl(telemetryServerUrl);
      logger.debug(`Connected to telemetry server on ${telemetryServerUrl}`);
    }
  }
}

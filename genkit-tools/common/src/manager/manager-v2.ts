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

import EventEmitter from 'events';
import getPort, { makeRange } from 'get-port';
import { WebSocket, WebSocketServer } from 'ws';
import {
  Action,
  RunActionResponse,
  RunActionResponseSchema,
} from '../types/action';
import * as apis from '../types/apis';
import { DevToolsInfo } from '../utils/utils';
import { BaseRuntimeManager } from './manager';
import { ProcessManager } from './process-manager';
import {
  GenkitToolsError,
  RuntimeEvent,
  RuntimeInfo,
  StreamingCallback,
} from './types';

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

interface ConnectedRuntime {
  ws: WebSocket;
  info: RuntimeInfo;
}

export class RuntimeManagerV2 extends BaseRuntimeManager {
  private _port?: number;
  private wss?: WebSocketServer;
  private runtimes: Map<string, ConnectedRuntime> = new Map();

  get port(): number | undefined {
    return this._port;
  }
  private pendingRequests: Map<
    number | string,
    { resolve: (value: any) => void; reject: (reason?: any) => void }
  > = new Map();
  private streamCallbacks: Map<number | string, StreamingCallback<any>> =
    new Map();
  private eventEmitter = new EventEmitter();
  private requestIdCounter = 0;

  constructor(
    telemetryServerUrl: string | undefined,
    readonly manageHealth: boolean,
    readonly projectRoot: string,
    override readonly processManager?: ProcessManager
  ) {
    super(telemetryServerUrl, processManager);
  }

  static async create(options: {
    telemetryServerUrl?: string;
    manageHealth?: boolean;
    projectRoot: string;
    processManager?: ProcessManager;
    reflectionV2Port?: number;
  }): Promise<RuntimeManagerV2> {
    const manager = new RuntimeManagerV2(
      options.telemetryServerUrl,
      options.manageHealth ?? true,
      options.projectRoot,
      options.processManager
    );
    await manager.startWebSocketServer(options.reflectionV2Port);
    return manager;
  }

  /**
   * Starts a WebSocket server.
   */
  private async startWebSocketServer(port?: number): Promise<{ port: number }> {
    if (!port) {
      port = await getPort({ port: makeRange(3200, 3400) });
    }
    this.wss = new WebSocketServer({ port });

    this._port = port;
    console.error(`Starting reflection server: ws://localhost:${port}`);

    this.wss.on('connection', (ws) => {
      ws.on('error', console.error);

      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString()) as JsonRpcMessage;
          this.handleMessage(ws, message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      });

      ws.on('close', () => {
        this.handleDisconnect(ws);
      });
    });
    return { port };
  }

  private handleMessage(ws: WebSocket, message: JsonRpcMessage) {
    if ('method' in message) {
      this.handleRequest(ws, message as JsonRpcRequest);
    } else {
      this.handleResponse(message as JsonRpcResponse);
    }
  }

  private handleRequest(ws: WebSocket, request: JsonRpcRequest) {
    switch (request.method) {
      case 'register':
        this.handleRegister(ws, request);
        break;
      case 'streamChunk':
        this.handleStreamChunk(request);
        break;
      case 'runActionState':
        // TODO: Handle runActionState for early trace info
        break;
      default:
        console.warn(`Unknown method: ${request.method}`);
    }
  }

  private handleRegister(ws: WebSocket, request: JsonRpcRequest) {
    const params = request.params;
    const runtimeInfo: RuntimeInfo = {
      id: params.id,
      pid: params.pid,
      name: params.name,
      genkitVersion: params.genkitVersion,
      reflectionApiSpecVersion: params.reflectionApiSpecVersion,
      reflectionServerUrl: `ws://localhost:${this.port}`, // Virtual URL for compatibility
      timestamp: new Date().toISOString(),
      projectName: params.name || 'Unknown', // Or derive from other means if needed
    };

    this.runtimes.set(runtimeInfo.id, { ws, info: runtimeInfo });
    this.eventEmitter.emit(RuntimeEvent.ADD, runtimeInfo);

    // Send success response
    if (request.id) {
      ws.send(
        JSON.stringify({
          jsonrpc: '2.0',
          result: null,
          id: request.id,
        })
      );
    }

    // Configure the runtime immediately
    this.notifyRuntime(runtimeInfo.id);
  }

  private handleStreamChunk(notification: JsonRpcRequest) {
    const { requestId, chunk } = notification.params;
    const callback = this.streamCallbacks.get(requestId);
    if (callback) {
      callback(chunk);
    }
  }

  private handleResponse(response: JsonRpcResponse) {
    const pending = this.pendingRequests.get(response.id);
    if (pending) {
      if (response.error) {
        const errorData = response.error.data || {};
        const massagedData = {
          ...errorData,
          stack: errorData.details?.stack,
          data: {
            genkitErrorMessage: errorData.message,
            genkitErrorDetails: errorData.details,
          },
        };
        const error = new GenkitToolsError(response.error.message);
        error.data = massagedData;
        pending.reject(error);
      } else {
        pending.resolve(response.result);
      }
      this.pendingRequests.delete(response.id);
    }
  }

  private handleDisconnect(ws: WebSocket) {
    for (const [id, runtime] of this.runtimes.entries()) {
      if (runtime.ws === ws) {
        this.runtimes.delete(id);
        this.eventEmitter.emit(RuntimeEvent.REMOVE, runtime.info);
        break;
      }
    }
  }

  private async sendRequest(
    runtimeId: string,
    method: string,
    params?: any
  ): Promise<any> {
    const runtime = this.runtimes.get(runtimeId);
    if (!runtime) {
      throw new Error(`Runtime ${runtimeId} not found`);
    }

    const id = ++this.requestIdCounter;
    const message: JsonRpcRequest = {
      jsonrpc: '2.0',
      method,
      params,
      id,
    };

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });
      runtime.ws.send(JSON.stringify(message));

      // Timeout cleanup
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error(`Request ${id} timed out`));
        }
      }, 30000);
    });
  }

  private sendNotification(runtimeId: string, method: string, params?: any) {
    const runtime = this.runtimes.get(runtimeId);
    if (!runtime) {
      console.warn(`Runtime ${runtimeId} not found, cannot send notification`);
      return;
    }
    const message: JsonRpcRequest = {
      jsonrpc: '2.0',
      method,
      params,
    };
    runtime.ws.send(JSON.stringify(message));
  }

  private notifyRuntime(runtimeId: string) {
    this.sendNotification(runtimeId, 'configure', {
      telemetryServerUrl: this.telemetryServerUrl,
    });
  }

  listRuntimes(): RuntimeInfo[] {
    return Array.from(this.runtimes.values()).map((r) => r.info);
  }

  getRuntimeById(id: string): RuntimeInfo | undefined {
    return this.runtimes.get(id)?.info;
  }

  getMostRecentRuntime(): RuntimeInfo | undefined {
    const runtimes = this.listRuntimes();
    if (runtimes.length === 0) return undefined;
    // Sort by timestamp descending? Or simply last added?
    // Map iteration order is insertion order, so last one is likely most recent if we just added them.
    // But let's trust the array.
    return runtimes[runtimes.length - 1];
  }

  getMostRecentDevUI(): DevToolsInfo | undefined {
    // Not applicable for V2 yet, or maybe handled differently
    return undefined;
  }

  onRuntimeEvent(
    listener: (eventType: RuntimeEvent, runtime: RuntimeInfo) => void
  ) {
    Object.values(RuntimeEvent).forEach((event) =>
      this.eventEmitter.on(event, (rt) => listener(event, rt))
    );
  }

  async listActions(
    input?: apis.ListActionsRequest
  ): Promise<Record<string, Action>> {
    const runtimeId = input?.runtimeId || this.getMostRecentRuntime()?.id;
    if (!runtimeId) {
      // No runtimes connected
      return {};
    }
    return this.sendRequest(runtimeId, 'listActions');
  }

  async close() {
    if (this.wss) {
      this.wss.close();
    }
  }

  async runAction(
    input: apis.RunActionRequest,
    streamingCallback?: StreamingCallback<any>
  ): Promise<RunActionResponse> {
    const runtimeId = input.runtimeId || this.getMostRecentRuntime()?.id;
    if (!runtimeId) {
      throw new Error('No runtime found');
    }

    const runtime = this.runtimes.get(runtimeId);
    if (!runtime) {
      throw new Error(`Runtime ${runtimeId} not found`);
    }

    const id = ++this.requestIdCounter;

    if (streamingCallback) {
      this.streamCallbacks.set(id, streamingCallback);
    }

    const message: JsonRpcRequest = {
      jsonrpc: '2.0',
      method: 'runAction',
      params: {
        ...input,
        stream: !!streamingCallback,
      },
      id,
    };

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });
      runtime.ws.send(JSON.stringify(message));

      // Timeout cleanup? Maybe longer for actions.
    })
      .then((result) => {
        return RunActionResponseSchema.parse(result);
      })
      .finally(() => {
        if (streamingCallback) {
          this.streamCallbacks.delete(id);
        }
      });
  }
}

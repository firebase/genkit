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

import getPort, { makeRange } from 'get-port';
import { WebSocketServer } from 'ws';
import * as apis from '../types/apis';
import { DevToolsInfo } from '../utils/utils';
import { BaseRuntimeManager } from './manager';
import { ProcessManager } from './process-manager';
import { RuntimeEvent, RuntimeInfo, StreamingCallback } from './types';
import { Action, RunActionResponse } from '../types/action';

export class RuntimeManagerV2 extends BaseRuntimeManager {
  private port?: number;

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
      port = await getPort({ port: makeRange(3100, 3200) });
    }
    const wss = new WebSocketServer({ port });

    this.port = port;
    console.log(`Starting WebSocket server on port ${port}`);

    wss.on('connection', (ws) => {
      ws.on('error', console.error);

      ws.on('message', (data) => {
        console.log('received: %s', data);
      });

      ws.send('hello world');
    });
    return { port };
  }

  listRuntimes(): RuntimeInfo[] {
    // TODO: Implement via WebSocket
    return [];
  }

  getRuntimeById(id: string): RuntimeInfo | undefined {
    // TODO: Implement via WebSocket
    return undefined;
  }

  getMostRecentRuntime(): RuntimeInfo | undefined {
    // TODO: Implement via WebSocket
    return undefined;
  }

  getMostRecentDevUI(): DevToolsInfo | undefined {
    // TODO: Implement via WebSocket
    return undefined;
  }

  onRuntimeEvent(
    listener: (eventType: RuntimeEvent, runtime: RuntimeInfo) => void
  ) {
    // TODO: Implement via WebSocket
  }

  async listActions(
    input?: apis.ListActionsRequest
  ): Promise<Record<string, Action>> {
    // TODO: Implement via WebSocket
    return {};
  }

  async runAction(
    input: apis.RunActionRequest,
    streamingCallback?: StreamingCallback<any>
  ): Promise<RunActionResponse> {
    // TODO: Implement via WebSocket
    throw new Error('Not implemented');
  }

}

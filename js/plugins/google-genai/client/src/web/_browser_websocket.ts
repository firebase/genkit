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
  WebSocketCallbacks,
  WebSocketFactory,
  WebSocket as Ws,
} from '../_websocket';

// TODO((b/401271082): re-enable lint once BrowserWebSocketFactory is
// implemented.
/*  eslint-disable @typescript-eslint/no-unused-vars */
export class BrowserWebSocketFactory implements WebSocketFactory {
  create(
    url: string,
    headers: Record<string, string>,
    callbacks: WebSocketCallbacks
  ): Ws {
    return new BrowserWebSocket(url, headers, callbacks);
  }
}

export class BrowserWebSocket implements Ws {
  private ws?: WebSocket;

  constructor(
    private readonly url: string,
    private readonly headers: Record<string, string>,
    private readonly callbacks: WebSocketCallbacks
  ) {
    console.debug(!!this.headers);
  }

  connect(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = this.callbacks.onopen;
    this.ws.onerror = this.callbacks.onerror;
    this.ws.onclose = this.callbacks.onclose;
    this.ws.onmessage = this.callbacks.onmessage;
  }

  send(message: string) {
    if (this.ws === undefined) {
      throw new Error('WebSocket is not connected');
    }

    this.ws.send(message);
  }

  close() {
    if (this.ws === undefined) {
      throw new Error('WebSocket is not connected');
    }

    this.ws.close();
  }
}

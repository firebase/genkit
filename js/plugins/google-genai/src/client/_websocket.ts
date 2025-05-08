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

export interface WebSocketCallbacks {
  onopen: () => void;
  // Following eslint rules are disabled because the callback types depend on
  // the implementation of the websocket.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onerror: (e: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onmessage: (e: any) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onclose: (e: any) => void;
}

export interface WebSocket {
  /**
   * Connects the socket to the server.
   */
  connect(): void;
  /**
   * Sends a message to the server.
   */
  send(message: string): void;
  /**
   * Closes the socket connection.
   */
  close(): void;
}

export interface WebSocketFactory {
  /**
   * Returns a new WebSocket instance.
   */
  create(
    url: string,
    headers: Record<string, string>,
    callbacks: WebSocketCallbacks
  ): WebSocket;
}

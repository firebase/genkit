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
import { crossError } from './_cross_error';

// TODO((b/401271082): re-enable lint once CrossWebSocketFactory is implemented.
/*  eslint-disable @typescript-eslint/no-unused-vars */
export class CrossWebSocketFactory implements WebSocketFactory {
  create(
    url: string,
    headers: Record<string, string>,
    callbacks: WebSocketCallbacks
  ): Ws {
    throw crossError();
  }
}

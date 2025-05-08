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

/**
 * Live client.
 *
 * @experimental
 */

import { ApiClient } from './_api_client';
import { Auth } from './_auth';
import * as t from './_transformers';
import { WebSocket, WebSocketCallbacks, WebSocketFactory } from './_websocket';
import * as converters from './converters/_live_converters';
import {
  contentToMldev,
  contentToVertex,
} from './converters/_models_converters';
import * as types from './types';

const FUNCTION_RESPONSE_REQUIRES_ID =
  'FunctionResponse request must have an `id` field from the response of a ToolCall.FunctionalCalls in Google AI.';

/**
 * Handles incoming messages from the WebSocket.
 *
 * @remarks
 * This function is responsible for parsing incoming messages, transforming them
 * into LiveServerMessages, and then calling the onmessage callback. Note that
 * the first message which is received from the server is a setupComplete
 * message.
 *
 * @param apiClient The ApiClient instance.
 * @param onmessage The user-provided onmessage callback (if any).
 * @param event The MessageEvent from the WebSocket.
 */
async function handleWebSocketMessage(
  apiClient: ApiClient,
  onmessage: (msg: types.LiveServerMessage) => void,
  event: MessageEvent
): Promise<void> {
  let serverMessage: types.LiveServerMessage;
  let data: types.LiveServerMessage;
  if (event.data instanceof Blob) {
    data = JSON.parse(await event.data.text()) as types.LiveServerMessage;
  } else {
    data = JSON.parse(event.data) as types.LiveServerMessage;
  }
  if (apiClient.isVertexAI()) {
    serverMessage = converters.liveServerMessageFromVertex(apiClient, data);
  } else {
    serverMessage = converters.liveServerMessageFromMldev(apiClient, data);
  }

  onmessage(serverMessage);
}

/**
   Live class encapsulates the configuration for live interaction with the
   Generative Language API. It embeds ApiClient for general API settings.

   @experimental
  */
export class Live {
  constructor(
    private readonly apiClient: ApiClient,
    private readonly auth: Auth,
    private readonly webSocketFactory: WebSocketFactory
  ) {}

  /**
     Establishes a connection to the specified model with the given
     configuration and returns a Session object representing that connection.

     @experimental

     @remarks

     @param params - The parameters for establishing a connection to the model.
     @return A live session.

     @example
     ```ts
     let model: string;
     if (GOOGLE_GENAI_USE_VERTEXAI) {
       model = 'gemini-2.0-flash-live-preview-04-09';
     } else {
       model = 'gemini-2.0-flash-live-001';
     }
     const session = await ai.live.connect({
       model: model,
       config: {
         responseModalities: [Modality.AUDIO],
       },
       callbacks: {
         onopen: () => {
           console.log('Connected to the socket.');
         },
         onmessage: (e: MessageEvent) => {
           console.log('Received message from the server: %s\n', debug(e.data));
         },
         onerror: (e: ErrorEvent) => {
           console.log('Error occurred: %s\n', debug(e.error));
         },
         onclose: (e: CloseEvent) => {
           console.log('Connection closed.');
         },
       },
     });
     ```
    */
  async connect(params: types.LiveConnectParameters): Promise<Session> {
    const websocketBaseUrl = this.apiClient.getWebsocketBaseUrl();
    const apiVersion = this.apiClient.getApiVersion();
    let url: string;
    const headers = mapToHeaders(this.apiClient.getDefaultHeaders());
    if (this.apiClient.isVertexAI()) {
      url = `${websocketBaseUrl}/ws/google.cloud.aiplatform.${apiVersion}.LlmBidiService/BidiGenerateContent`;
      await this.auth.addAuthHeaders(headers);
    } else {
      const apiKey = this.apiClient.getApiKey();
      url = `${websocketBaseUrl}/ws/google.ai.generativelanguage.${apiVersion}.GenerativeService.BidiGenerateContent?key=${apiKey}`;
    }

    let onopenResolve: (value: unknown) => void = () => {};
    const onopenPromise = new Promise((resolve: (value: unknown) => void) => {
      onopenResolve = resolve;
    });

    const callbacks: types.LiveCallbacks = params.callbacks;

    const onopenAwaitedCallback = function () {
      callbacks?.onopen?.();
      onopenResolve({});
    };

    const apiClient = this.apiClient;

    const websocketCallbacks: WebSocketCallbacks = {
      onopen: onopenAwaitedCallback,
      onmessage: (event: MessageEvent) => {
        void handleWebSocketMessage(apiClient, callbacks.onmessage, event);
      },
      onerror:
        callbacks?.onerror ??
        function (e: ErrorEvent) {
          void e;
        },
      onclose:
        callbacks?.onclose ??
        function (e: CloseEvent) {
          void e;
        },
    };

    const conn = this.webSocketFactory.create(
      url,
      headersToMap(headers),
      websocketCallbacks
    );
    conn.connect();
    // Wait for the websocket to open before sending requests.
    await onopenPromise;

    let transformedModel = t.tModel(this.apiClient, params.model);
    if (
      this.apiClient.isVertexAI() &&
      transformedModel.startsWith('publishers/')
    ) {
      const project = this.apiClient.getProject();
      const location = this.apiClient.getLocation();
      transformedModel =
        `projects/${project}/locations/${location}/` + transformedModel;
    }

    let clientMessage: Record<string, unknown> = {};

    if (
      this.apiClient.isVertexAI() &&
      params.config?.responseModalities === undefined
    ) {
      // Set default to AUDIO to align with MLDev API.
      if (params.config === undefined) {
        params.config = { responseModalities: [types.Modality.AUDIO] };
      } else {
        params.config.responseModalities = [types.Modality.AUDIO];
      }
    }
    if (params.config?.generationConfig) {
      // Raise deprecation warning for generationConfig.
      console.warn(
        'Setting `LiveConnectConfig.generation_config` is deprecated, please set the fields on `LiveConnectConfig` directly. This will become an error in a future version (not before Q3 2025).'
      );
    }
    const liveConnectParameters: types.LiveConnectParameters = {
      model: transformedModel,
      config: params.config,
      callbacks: params.callbacks,
    };
    if (this.apiClient.isVertexAI()) {
      clientMessage = converters.liveConnectParametersToVertex(
        this.apiClient,
        liveConnectParameters
      );
    } else {
      clientMessage = converters.liveConnectParametersToMldev(
        this.apiClient,
        liveConnectParameters
      );
    }
    delete clientMessage['config'];
    conn.send(JSON.stringify(clientMessage));
    return new Session(conn, this.apiClient);
  }
}

const defaultLiveSendClientContentParamerters: types.LiveSendClientContentParameters =
  {
    turnComplete: true,
  };

/**
   Represents a connection to the API.

   @experimental
  */
export class Session {
  constructor(
    readonly conn: WebSocket,
    private readonly apiClient: ApiClient
  ) {}

  private tLiveClientContent(
    apiClient: ApiClient,
    params: types.LiveSendClientContentParameters
  ): types.LiveClientMessage {
    if (params.turns !== null && params.turns !== undefined) {
      let contents: types.Content[] = [];
      try {
        contents = t.tContents(
          apiClient,
          params.turns as types.ContentListUnion
        );
        if (apiClient.isVertexAI()) {
          contents = contents.map((item) => contentToVertex(apiClient, item));
        } else {
          contents = contents.map((item) => contentToMldev(apiClient, item));
        }
      } catch {
        throw new Error(
          `Failed to parse client content "turns", type: '${typeof params.turns}'`
        );
      }
      return {
        clientContent: { turns: contents, turnComplete: params.turnComplete },
      };
    }

    return {
      clientContent: { turnComplete: params.turnComplete },
    };
  }

  private tLiveClienttToolResponse(
    apiClient: ApiClient,
    params: types.LiveSendToolResponseParameters
  ): types.LiveClientMessage {
    let functionResponses: types.FunctionResponse[] = [];

    if (params.functionResponses == null) {
      throw new Error('functionResponses is required.');
    }

    if (!Array.isArray(params.functionResponses)) {
      functionResponses = [params.functionResponses];
    } else {
      functionResponses = params.functionResponses;
    }

    if (functionResponses.length === 0) {
      throw new Error('functionResponses is required.');
    }

    for (const functionResponse of functionResponses) {
      if (
        typeof functionResponse !== 'object' ||
        functionResponse === null ||
        !('name' in functionResponse) ||
        !('response' in functionResponse)
      ) {
        throw new Error(
          `Could not parse function response, type '${typeof functionResponse}'.`
        );
      }
      if (!apiClient.isVertexAI() && !('id' in functionResponse)) {
        throw new Error(FUNCTION_RESPONSE_REQUIRES_ID);
      }
    }

    const clientMessage: types.LiveClientMessage = {
      toolResponse: { functionResponses: functionResponses },
    };
    return clientMessage;
  }

  /**
    Send a message over the established connection.

    @param params - Contains two **optional** properties, `turns` and
        `turnComplete`.

      - `turns` will be converted to a `Content[]`
      - `turnComplete: true` [default] indicates that you are done sending
        content and expect a response. If `turnComplete: false`, the server
        will wait for additional messages before starting generation.

    @experimental

    @remarks
    There are two ways to send messages to the live API:
    `sendClientContent` and `sendRealtimeInput`.

    `sendClientContent` messages are added to the model context **in order**.
    Having a conversation using `sendClientContent` messages is roughly
    equivalent to using the `Chat.sendMessageStream`, except that the state of
    the `chat` history is stored on the API server instead of locally.

    Because of `sendClientContent`'s order guarantee, the model cannot respons
    as quickly to `sendClientContent` messages as to `sendRealtimeInput`
    messages. This makes the biggest difference when sending objects that have
    significant preprocessing time (typically images).

    The `sendClientContent` message sends a `Content[]`
    which has more options than the `Blob` sent by `sendRealtimeInput`.

    So the main use-cases for `sendClientContent` over `sendRealtimeInput` are:

    - Sending anything that can't be represented as a `Blob` (text,
    `sendClientContent({turns="Hello?"}`)).
    - Managing turns when not using audio input and voice activity detection.
      (`sendClientContent({turnComplete:true})` or the short form
    `sendClientContent()`)
    - Prefilling a conversation context
      ```
      sendClientContent({
          turns: [
            Content({role:user, parts:...}),
            Content({role:user, parts:...}),
            ...
          ]
      })
      ```
    @experimental
   */
  sendClientContent(params: types.LiveSendClientContentParameters) {
    params = {
      ...defaultLiveSendClientContentParamerters,
      ...params,
    };

    const clientMessage: types.LiveClientMessage = this.tLiveClientContent(
      this.apiClient,
      params
    );
    this.conn.send(JSON.stringify(clientMessage));
  }

  /**
    Send a realtime message over the established connection.

    @param params - Contains one property, `media`.

      - `media` will be converted to a `Blob`

    @experimental

    @remarks
    Use `sendRealtimeInput` for realtime audio chunks and video frames (images).

    With `sendRealtimeInput` the api will respond to audio automatically
    based on voice activity detection (VAD).

    `sendRealtimeInput` is optimized for responsivness at the expense of
    deterministic ordering guarantees. Audio and video tokens are to the
    context when they become available.

    Note: The Call signature expects a `Blob` object, but only a subset
    of audio and image mimetypes are allowed.
   */
  sendRealtimeInput(params: types.LiveSendRealtimeInputParameters) {
    let clientMessage: types.LiveClientMessage = {};

    if (this.apiClient.isVertexAI()) {
      clientMessage = {
        realtimeInput: converters.liveSendRealtimeInputParametersToVertex(
          this.apiClient,
          params
        ),
      };
    } else {
      clientMessage = {
        realtimeInput: converters.liveSendRealtimeInputParametersToMldev(
          this.apiClient,
          params
        ),
      };
    }
    this.conn.send(JSON.stringify(clientMessage));
  }

  /**
    Send a function response message over the established connection.

    @param params - Contains property `functionResponses`.

      - `functionResponses` will be converted to a `functionResponses[]`

    @remarks
    Use `sendFunctionResponse` to reply to `LiveServerToolCall` from the server.

    Use {@link types.LiveConnectConfig#tools} to configure the callable functions.

    @experimental
   */
  sendToolResponse(params: types.LiveSendToolResponseParameters) {
    if (params.functionResponses == null) {
      throw new Error('Tool response parameters are required.');
    }

    const clientMessage: types.LiveClientMessage =
      this.tLiveClienttToolResponse(this.apiClient, params);
    this.conn.send(JSON.stringify(clientMessage));
  }

  /**
     Terminates the WebSocket connection.

     @experimental

     @example
     ```ts
     let model: string;
     if (GOOGLE_GENAI_USE_VERTEXAI) {
       model = 'gemini-2.0-flash-live-preview-04-09';
     } else {
       model = 'gemini-2.0-flash-live-001';
     }
     const session = await ai.live.connect({
       model: model,
       config: {
         responseModalities: [Modality.AUDIO],
       }
     });

     session.close();
     ```
   */
  close() {
    this.conn.close();
  }
}

// Converts an headers object to a "map" object as expected by the WebSocket
// constructor. We use this as the Auth interface works with Headers objects
// while the WebSocket constructor takes a map.
function headersToMap(headers: Headers): Record<string, string> {
  const headerMap: Record<string, string> = {};
  headers.forEach((value, key) => {
    headerMap[key] = value;
  });
  return headerMap;
}

// Converts a "map" object to a headers object. We use this as the Auth
// interface works with Headers objects while the API client default headers
// returns a map.
function mapToHeaders(map: Record<string, string>): Headers {
  const headers = new Headers();
  for (const [key, value] of Object.entries(map)) {
    headers.append(key, value);
  }
  return headers;
}

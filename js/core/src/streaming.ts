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

import { GenkitError } from './error';

export class StreamNotFoundError extends GenkitError {
  constructor(message: string) {
    super({ status: 'NOT_FOUND', message });
    this.name = 'StreamNotFoundError';
  }
}

export interface ActionStreamInput<S, O> {
  write(chunk: S): Promise<void>;
  done(output: O): Promise<void>;
  error(err: any): Promise<void>;
}

export type ActionStreamSubscriber<S, O> = {
  onChunk: (chunk: S) => void;
  onDone: (output: O) => void;
  onError: (error: any) => void;
};

export interface StreamManager {
  open<S, O>(streamId: string): Promise<ActionStreamInput<S, O>>;
  subscribe<S, O>(
    streamId: string,
    options: ActionStreamSubscriber<S, O>
  ): Promise<{ unsubscribe: () => void }>;
}

type StreamState<S, O> =
  | {
      status: 'open';
      chunks: S[];
      subscribers: ActionStreamSubscriber<S, O>[];
      lastTouched: number;
    }
  | { status: 'done'; chunks: S[]; output: O; lastTouched: number }
  | { status: 'error'; chunks: S[]; error: any; lastTouched: number };

export class InMemoryStreamManager implements StreamManager {
  private streams: Map<string, StreamState<any, any>> = new Map();

  constructor(private options: { ttlSeconds?: number } = {}) {}

  private _cleanup() {
    const ttl = (this.options.ttlSeconds ?? 5 * 60) * 1000;
    const now = Date.now();
    for (const [streamId, stream] of this.streams.entries()) {
      if (stream.status !== 'open' && now - stream.lastTouched > ttl) {
        this.streams.delete(streamId);
      }
    }
  }

  async open<S, O>(streamId: string): Promise<ActionStreamInput<S, O>> {
    this._cleanup();
    if (this.streams.has(streamId)) {
      throw new Error(`Stream with id ${streamId} already exists.`);
    }
    this.streams.set(streamId, {
      status: 'open',
      chunks: [],
      subscribers: [],
      lastTouched: Date.now(),
    });

    return {
      write: async (chunk: S) => {
        const stream = this.streams.get(streamId);
        if (stream?.status === 'open') {
          stream.chunks.push(chunk);
          stream.subscribers.forEach((s) => s.onChunk(chunk));
          stream.lastTouched = Date.now();
        }
      },
      done: async (output: O) => {
        const stream = this.streams.get(streamId);
        if (stream?.status === 'open') {
          this.streams.set(streamId, {
            status: 'done',
            chunks: stream.chunks,
            output,
            lastTouched: Date.now(),
          });
          stream.subscribers.forEach((s) => s.onDone(output));
        }
      },
      error: async (err: any) => {
        const stream = this.streams.get(streamId);
        if (stream?.status === 'open') {
          stream.subscribers.forEach((s) => s.onError(err));
          this.streams.set(streamId, {
            status: 'error',
            chunks: stream.chunks,
            error: err,
            lastTouched: Date.now(),
          });
        }
      },
    };
  }

  async subscribe<S, O>(
    streamId: string,
    subscriber: ActionStreamSubscriber<S, O>
  ): Promise<{ unsubscribe: () => void }> {
    const stream = this.streams.get(streamId);
    if (!stream) {
      throw new StreamNotFoundError(`Stream with id ${streamId} not found.`);
    }

    if (stream.status === 'done') {
      for (const chunk of stream.chunks) {
        subscriber.onChunk(chunk);
      }
      subscriber.onDone(stream.output);
    } else if (stream.status === 'error') {
      for (const chunk of stream.chunks) {
        subscriber.onChunk(chunk);
      }
      subscriber.onError(stream.error);
    } else {
      stream.chunks.forEach((chunk) => subscriber.onChunk(chunk));
      stream.subscribers.push(subscriber);
    }

    return {
      unsubscribe: () => {
        const currentStream = this.streams.get(streamId);
        if (currentStream?.status === 'open') {
          const index = currentStream.subscribers.indexOf(subscriber);
          if (index > -1) {
            currentStream.subscribers.splice(index, 1);
          }
        }
      },
    };
  }
}

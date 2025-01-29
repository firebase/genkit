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

// NOTE: This file is pulled into client code and cannot have any Node-only
// dependencies.

/**
 * A handle to a promise and its resolvers.
 */
export interface Task<T> {
  resolve: (result: T) => void;
  reject: (err: unknown) => void;
  promise: Promise<T>;
}

/** Utility for creating Tasks. */
function createTask<T>(): Task<T> {
  let resolve: unknown, reject: unknown;
  let promise = new Promise<T>((res, rej) => ([resolve, reject] = [res, rej]));
  return {
    resolve: resolve as Task<T>['resolve'],
    reject: reject as Task<T>['reject'],
    promise,
  };
}

/**
 * A class designed to help turn repeated callbacks into async iterators.
 * Based loosely on a combination of Go channels and Promises.
 */
export class Channel<T> implements AsyncIterable<T> {
  private ready: Task<void> = createTask<void>();
  private buffer: (T | null)[] = [];
  private err: unknown = null;

  send(value: T): void {
    this.buffer.push(value);
    this.ready.resolve();
  }

  close(): void {
    this.buffer.push(null);
    this.ready.resolve();
  }

  error(err: unknown): void {
    this.err = err;
    // Note: we must call this.ready.reject here in case we get an error even before the stream is initiated,
    // however we cannot rely on this.ready.reject because it will be ignored if ready.resolved has already
    // been called, so this.err will be checked in the iterator as well.
    this.ready.reject(err);
  }

  [Symbol.asyncIterator](): AsyncIterator<T> {
    return {
      next: async (): Promise<IteratorResult<T>> => {
        if (this.err) {
          throw this.err;
        }

        if (!this.buffer.length) {
          await this.ready.promise;
        }
        const value = this.buffer.shift()!;
        if (!this.buffer.length) {
          this.ready = createTask<void>();
        }

        return {
          value,
          done: !value,
        };
      },
    };
  }
}

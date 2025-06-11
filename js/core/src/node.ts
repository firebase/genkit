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

import { performance } from 'node:perf_hooks';
import { AlsAsyncStore } from './als-async-store.js';
import { NodeGenkitOtel } from './node-otel.js';
import { _setAsyncStoreFactory, Registry } from './registry.js';
import { _setGenkitOtel } from './tracing.js';
import { _setFetchFn, _setPerformanceNowFn } from './utils.js';
export * from './reflection.js';

_setGenkitOtel(new NodeGenkitOtel());
_setPerformanceNowFn(() => performance.now());
_setFetchFn(import('node-fetch').then((d) => d.default as any));

export class NodeRegistry extends Registry {
  constructor(parent?: NodeRegistry) {
    if (parent) {
      super(parent);
    } else {
      const store = new AlsAsyncStore();
      const asyncStoreFactory = () => store;

      super({ asyncStoreFactory });
      _setAsyncStoreFactory(asyncStoreFactory);
    }
  }

  child(): Registry {
    return new NodeRegistry(this);
  }
}

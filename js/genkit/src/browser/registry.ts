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

import {
  AsyncStore,
  Registry,
  _setAsyncStoreFactory,
} from '@genkit-ai/core/registry';
import { _setGenkitOtel } from '@genkit-ai/core/tracing';
import 'zone.js';

// TODO: implement instrumentation.
_setGenkitOtel({
  enableTelemetry(telemetryConfig) {},
  async flushMetrics() {},
  async flushTracing() {},
  async shutdown() {},
});

/**
 * Implementation of AsyncStore using zone.js.
 */
class BrowserAsyncStore implements AsyncStore {
  getStore<T>(key: string): T | undefined {
    return Zone.current.get(key);
  }

  run<T, R>(key: string, value: T, callback: () => R): R {
    const id = 'run:' + key + ':' + Math.random().toString(36);
    const zone = Zone.current.fork({
      name: id,
      properties: { [key]: value },
    });
    return zone.run(callback, undefined);
  }
}

export class BrowserRegistry extends Registry {
  constructor(parent?: BrowserRegistry) {
    if (parent) {
      super(parent);
    } else {
      const store = new BrowserAsyncStore();
      const asyncStoreFactory = () => store;

      super({ asyncStoreFactory });
      _setAsyncStoreFactory(asyncStoreFactory);
    }
  }

  child(): Registry {
    return new BrowserRegistry(this);
  }
}

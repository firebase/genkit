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

import type { Context } from '@opentelemetry/api';
import type {
  ReadableSpan,
  Span,
  SpanProcessor,
} from '@opentelemetry/sdk-trace-base';

/**
 * A {SpanProcessor} wrapper that supports exporting to multiple {SpanProcessor}s.
 */
export class MultiSpanProcessor implements SpanProcessor {
  constructor(private processors: SpanProcessor[]) {}

  forceFlush(): Promise<void> {
    return Promise.all(this.processors.map((p) => p.forceFlush())).then();
  }

  onStart(span: Span, parentContext: Context): void {
    this.processors.map((p) => p.onStart(span, parentContext));
  }

  onEnd(span: ReadableSpan): void {
    this.processors.map((p) => p.onEnd(span));
  }

  async shutdown(): Promise<void> {
    return Promise.all(this.processors.map((p) => p.shutdown())).then();
  }
}

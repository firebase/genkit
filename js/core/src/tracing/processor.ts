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
import { ATTR_PREFIX } from './instrumentation.js';

// Experimental, WIP

export class GenkitSpanProcessorWrapper implements SpanProcessor {
  constructor(private processor: SpanProcessor) {}

  forceFlush(): Promise<void> {
    return this.processor.forceFlush();
  }

  onStart(span: Span, parentContext: Context): void {
    return this.processor.onStart(span, parentContext);
  }

  onEnd(span: ReadableSpan): void {
    if (
      Object.keys(span.attributes).find((k) => k.startsWith(ATTR_PREFIX + ':'))
    ) {
      return this.processor.onEnd(new FilteringReadableSpanProxy(span));
    } else {
      return this.processor.onEnd(span);
    }
  }

  async shutdown(): Promise<void> {
    return this.processor.shutdown();
  }
}

class FilteringReadableSpanProxy implements ReadableSpan {
  constructor(private span: ReadableSpan) {}

  get name() {
    return this.span.name;
  }
  get kind() {
    return this.span.kind;
  }
  get parentSpanId() {
    return this.span.parentSpanId;
  }
  get startTime() {
    return this.span.startTime;
  }
  get endTime() {
    return this.span.endTime;
  }
  get status() {
    return this.span.status;
  }
  get attributes() {
    const out = {} as Record<string, any>;
    for (const [key, value] of Object.entries(this.span.attributes)) {
      if (!key.startsWith(ATTR_PREFIX + ':')) {
        out[key] = value;
      }
    }
    return out;
  }
  get links() {
    return this.span.links;
  }
  get events() {
    return this.span.events;
  }
  get duration() {
    return this.span.duration;
  }
  get ended() {
    return this.span.ended;
  }
  get resource() {
    return this.span.resource;
  }
  get instrumentationLibrary() {
    return this.span.instrumentationLibrary;
  }
  get droppedAttributesCount() {
    return this.span.droppedAttributesCount;
  }
  get droppedEventsCount() {
    return this.span.droppedEventsCount;
  }
  get droppedLinksCount() {
    return this.span.droppedLinksCount;
  }

  spanContext() {
    return this.span.spanContext();
  }
}

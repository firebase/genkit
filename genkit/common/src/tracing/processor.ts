import { Context } from '@opentelemetry/api';
import {
  ReadableSpan,
  SpanProcessor,
  Span,
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
    console.log(
      'FilteringReadableSpanProxy get attributes',
      this.span.attributes
    );
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

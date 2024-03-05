import { Context } from '@opentelemetry/api';
import {
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

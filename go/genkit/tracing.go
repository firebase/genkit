package genkit

import (
	"context"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

// This file contains code translated from js/common/src/tracing/*.ts.

// tracer is an OpenTelemetry object that creates traces.
// Use the same one for the lifetime of the process.
var tracer = otel.Tracer("genkit-tracer")

const spanTypeAttr = "genkit:type"

// runInNewSpan runs f on input in a new span with the given name.
// The attrs map provides the span's initial attributes.
func runInNewSpan[I, O any](
	ctx context.Context,
	name, spanType string,
	input I,
	f func(context.Context, I) (O, error),
) (O, error) {
	log := logger(ctx)
	log.Debug("span start", "name", name)
	defer log.Debug("span end", "name", name)
	ctx, span := tracer.Start(ctx, name, trace.WithAttributes(attribute.String(spanTypeAttr, spanType)))
	defer span.End()
	// TODO: create and populate a genkit-specific SpanMetadata value.
	return f(ctx, input)
}

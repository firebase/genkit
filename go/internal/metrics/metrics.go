// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package metrics

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/metric"
)

type metricInstruments struct {
	actionCounter   metric.Int64Counter
	actionLatencies metric.Int64Histogram
	flowCounter     metric.Int64Counter
	flowLatencies   metric.Int64Histogram
}

// Delay instrument creation until first use to ensure that
// a MeterProvider has been set (see, e.g., plugins/googlecloud).
var fetchInstruments = sync.OnceValue(func() *metricInstruments {
	insts, err := initInstruments()
	if err != nil {
		// Do not stop the program because we can't collect metrics.
		slog.Default().Error("metric initialization failed; no metrics will be collected", "err", err)
		return nil
	}
	return insts
})

func initInstruments() (*metricInstruments, error) {
	meter := otel.Meter("genkit")
	var err error
	insts := &metricInstruments{}
	insts.actionCounter, err = meter.Int64Counter("genkit/action/requests")
	if err != nil {
		return nil, err
	}
	insts.actionLatencies, err = meter.Int64Histogram("genkit/action/latency", metric.WithUnit("ms"))
	if err != nil {
		return nil, err
	}
	insts.flowCounter, err = meter.Int64Counter("genkit/flow/requests")
	if err != nil {
		return nil, err
	}
	insts.flowLatencies, err = meter.Int64Histogram("genkit/flow/latency", metric.WithUnit("ms"))
	if err != nil {
		return nil, err
	}
	return insts, nil
}

func WriteActionSuccess(ctx context.Context, actionName string, latency time.Duration) {
	recordAction(ctx, latency,
		attribute.String("name", actionName),
		attribute.String("source", "go"))
}

func WriteActionFailure(ctx context.Context, actionName string, latency time.Duration, err error) {
	recordAction(ctx, latency, attribute.String("name", actionName),
		attribute.Int("errorCode", errorCode(err)),
		// TODO: Mitigate against high-cardinality dimensions that arise from
		// many different error messages, perhaps by taking a prefix of the error
		// message.
		attribute.String("errorMessage", err.Error()),
		attribute.String("source", "go"))
}

func errorCode(err error) int {
	// Support errors that have a numeric code.
	if cerr, ok := err.(interface{ Code() int }); ok {
		return cerr.Code()
	}
	return 0
}

func recordAction(ctx context.Context, latency time.Duration, attrs ...attribute.KeyValue) {
	if insts := fetchInstruments(); insts != nil {
		recordCountAndLatency(ctx, insts.actionCounter, insts.actionLatencies, latency, attrs...)
	}
}

func WriteFlowSuccess(ctx context.Context, flowName string, latency time.Duration) {
	recordFlow(ctx, latency,
		attribute.String("name", flowName),
		attribute.String("source", "go"))
}

func WriteFlowFailure(ctx context.Context, flowName string, latency time.Duration, err error) {
	recordAction(ctx, latency, attribute.String("name", flowName),
		attribute.Int("errorCode", errorCode(err)),
		// TODO: Mitigate against high-cardinality dimensions that arise from
		// many different error messages, perhaps by taking a prefix of the error
		// message.
		attribute.String("errorMessage", err.Error()),
		attribute.String("source", "go"))
}

func recordFlow(ctx context.Context, latency time.Duration, attrs ...attribute.KeyValue) {
	if insts := fetchInstruments(); insts != nil {
		recordCountAndLatency(ctx, insts.flowCounter, insts.flowLatencies, latency, attrs...)
	}
}

func recordCountAndLatency(ctx context.Context, counter metric.Int64Counter, hist metric.Int64Histogram, latency time.Duration, attrs ...attribute.KeyValue) {
	opt := metric.WithAttributes(attrs...)
	counter.Add(ctx, 1, opt)
	hist.Record(ctx, latency.Milliseconds(), opt)

}

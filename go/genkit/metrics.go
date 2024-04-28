// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package genkit

import (
	"context"
	"sync"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/metric"
)

type metricInstruments struct {
	actionCounter   metric.Int64Counter
	actionLatencies metric.Int64Histogram
}

// Delay instrument creation until first use to ensure that
// a MeterProvider has been set (see, e.g., plugins/googlecloud).
var fetchInstruments = sync.OnceValue(func() *metricInstruments {
	insts, err := initInstruments()
	if err != nil {
		// Do not stop the program because we can't collect metrics.
		logger(context.Background()).Error("metric initialization failed; no metrics will be collected", "err", err)
		return nil
	}
	return insts
})

func initInstruments() (*metricInstruments, error) {
	meter := otel.Meter("genkit")
	var err error
	insts := &metricInstruments{}
	insts.actionCounter, err = meter.Int64Counter("action.requests")
	if err != nil {
		return nil, err
	}
	insts.actionLatencies, err = meter.Int64Histogram("action.latency", metric.WithUnit("ms"))
	if err != nil {
		return nil, err
	}
	return insts, nil
}

func writeActionSuccess(ctx context.Context, actionName string, latency time.Duration) {
	recordAction(ctx, latency, attribute.String("actionName", actionName))
}

func writeActionFailure(ctx context.Context, actionName string, latency time.Duration, err error) {
	code := 0
	// Support errors that have a numeric code.
	if cerr, ok := err.(interface{ Code() int }); ok {
		code = cerr.Code()
	}
	recordAction(ctx, latency, attribute.String("actionName", actionName),
		attribute.Int("errorCode", code),
		// TODO(jba): Mitigate against high-cardinality dimensions that arise from
		// many different error messages, perhaps by taking a prefix of the error
		// message.
		attribute.String("errorMessage", err.Error()))
}

func recordAction(ctx context.Context, latency time.Duration, attrs ...attribute.KeyValue) {
	if insts := fetchInstruments(); insts != nil {
		opt := metric.WithAttributes(attrs...)
		insts.actionCounter.Add(ctx, 1, opt)
		insts.actionLatencies.Record(ctx, latency.Milliseconds(), opt)
	}
}

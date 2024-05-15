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

// The googlecloud package supports telemetry (tracing, metrics and logging) using
// Google Cloud services.
package googlecloud

// See js/plugins/google-cloud/src/gcpOpenTelemetry.ts.

import (
	"context"
	"log/slog"
	"os"
	"time"

	"cloud.google.com/go/logging"
	mexporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/metric"
	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"github.com/firebase/genkit/go/genkit"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

type Options struct {
	// Export to Google Cloud even in the dev environment.
	ForceExport bool

	// The interval for exporting metric data.
	// The default is 60 seconds.
	MetricInterval time.Duration

	// The minimum level at which logs will be written.
	// Defaults to [slog.LevelInfo].
	LogLevel slog.Leveler
}

// Init initializes all telemetry in this package.
// In the dev environment, this does nothing unless [Options.ForceExport] is true.
func Init(ctx context.Context, projectID string, opts *Options) error {
	if opts == nil {
		opts = &Options{}
	}
	shouldExport := opts.ForceExport || os.Getenv("GENKIT_ENV") != "dev"
	if !shouldExport {
		return nil
	}
	// Add a SpanProcessor for tracing.
	texp, err := texporter.New(texporter.WithProjectID(projectID))
	if err != nil {
		return err
	}
	aexp := &adjustingTraceExporter{texp}
	genkit.RegisterSpanProcessor(sdktrace.NewBatchSpanProcessor(aexp))
	if err := setMeterProvider(projectID, opts.MetricInterval); err != nil {
		return err
	}
	return setLogHandler(projectID, opts.LogLevel)
}

func setMeterProvider(projectID string, interval time.Duration) error {
	mexp, err := mexporter.New(mexporter.WithProjectID(projectID))
	if err != nil {
		return err
	}
	r := sdkmetric.NewPeriodicReader(mexp, sdkmetric.WithInterval(interval))
	mp := sdkmetric.NewMeterProvider(sdkmetric.WithReader(r))
	otel.SetMeterProvider(mp)
	return nil
}

type adjustingTraceExporter struct {
	e sdktrace.SpanExporter
}

func (e *adjustingTraceExporter) ExportSpans(ctx context.Context, spanData []sdktrace.ReadOnlySpan) error {
	var adjusted []sdktrace.ReadOnlySpan
	for _, s := range spanData {
		adjusted = append(adjusted, adjustedSpan{s})
	}
	return e.e.ExportSpans(ctx, adjusted)
}

func (e *adjustingTraceExporter) Shutdown(ctx context.Context) error {
	return e.e.Shutdown(ctx)
}

type adjustedSpan struct {
	sdktrace.ReadOnlySpan
}

func (s adjustedSpan) Attributes() []attribute.KeyValue {
	// Omit input and output, which may contain PII.
	var ts []attribute.KeyValue
	for _, a := range s.ReadOnlySpan.Attributes() {
		if a.Key == "genkit:input" || a.Key == "genkit:output" {
			continue
		}
		ts = append(ts, a)
	}
	// Add an attribute if there is an error.
	if s.ReadOnlySpan.Status().Code == codes.Error {
		ts = append(ts, attribute.String("/http/status_code", "599"))
	}
	return ts
}

func setLogHandler(projectID string, level slog.Leveler) error {
	c, err := logging.NewClient(context.Background(), "projects/"+projectID)
	if err != nil {
		return err
	}
	logger := c.Logger("genkit_log")
	slog.SetDefault(slog.New(newHandler(level, logger.Log)))
	return nil
}

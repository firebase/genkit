// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// The googlecloud package supports telemetry (tracing, metrics and logging) using
// Google Cloud services.
package googlecloud

// See js/plugins/google-cloud/src/gcpOpenTelemetry.ts.

import (
	"context"
	"errors"
	"fmt"
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

// Config provides configuration options for the Init function.
type Config struct {
	// ID of the project to use. Required.
	ProjectID string
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
func Init(ctx context.Context, g *genkit.Genkit, cfg Config) (err error) {
	defer func() {
		if err != nil {
			err = fmt.Errorf("googlecloud.Init: %w", err)
		}
	}()

	if cfg.ProjectID == "" {
		return errors.New("config missing ProjectID")
	}
	shouldExport := cfg.ForceExport || os.Getenv("GENKIT_ENV") != "dev"
	if !shouldExport {
		return nil
	}
	// Add a SpanProcessor for tracing.
	texp, err := texporter.New(texporter.WithProjectID(cfg.ProjectID))
	if err != nil {
		return err
	}
	aexp := &adjustingTraceExporter{texp}
	genkit.RegisterSpanProcessor(g, sdktrace.NewBatchSpanProcessor(aexp))
	if err := setMeterProvider(cfg.ProjectID, cfg.MetricInterval); err != nil {
		return err
	}
	return setLogHandler(cfg.ProjectID, cfg.LogLevel)
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

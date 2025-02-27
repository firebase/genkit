// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package telemetryplugin

import (
	"context"
	"log/slog"
	"os"
	"time"

	// [START import]
	// Import the Genkit core library.

	"github.com/firebase/genkit/go/genkit"

	// Import the OpenTelemetry libraries.
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/trace"
	// [END import]
)

// [START config]
type Config struct {
	// Export even in the dev environment.
	ForceExport bool

	// The interval for exporting metric data.
	// The default is 60 seconds.
	MetricInterval time.Duration

	// The minimum level at which logs will be written.
	// Defaults to [slog.LevelInfo].
	LogLevel slog.Leveler
}

// [END config]

func Init(cfg Config) error {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		return err
	}

	// [START shouldexport]
	shouldExport := cfg.ForceExport || os.Getenv("GENKIT_ENV") != "dev"
	if !shouldExport {
		return nil
	}
	// [END shouldexport]

	// [START registerspanexporter]
	spanProcessor := trace.NewBatchSpanProcessor(YourCustomSpanExporter{})
	genkit.RegisterSpanProcessor(g, spanProcessor)
	// [END registerspanexporter]

	// [START registermetricexporter]
	r := metric.NewPeriodicReader(
		YourCustomMetricExporter{},
		metric.WithInterval(cfg.MetricInterval),
	)
	mp := metric.NewMeterProvider(metric.WithReader(r))
	otel.SetMeterProvider(mp)
	// [END registermetricexporter]

	// [START registerlogexporter]
	logger := slog.New(YourCustomHandler{
		Options: &slog.HandlerOptions{Level: cfg.LogLevel},
	})
	slog.SetDefault(logger)
	// [END registerlogexporter]

	return nil
}

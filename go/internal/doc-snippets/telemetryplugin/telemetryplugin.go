// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package telemetryplugin

import (
	"log/slog"
	"os"
	"time"

	// [START import]
	// Import the OpenTelemetry libraries.
	"go.opentelemetry.io/otel"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	"go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
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

// [START enablecustom]
// EnableCustomTelemetry enables telemetry export to your custom telemetry provider.
// This function should be called before genkit.Init().
//
// Example usage:
//
//	// Enable custom telemetry
//	telemetryplugin.EnableCustomTelemetry(&telemetryplugin.Config{
//		ForceExport:    true,
//		MetricInterval: 30 * time.Second,
//		LogLevel:       slog.LevelDebug,
//	})
//	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
func EnableCustomTelemetry(cfg *Config) {
	if cfg == nil {
		cfg = &Config{
			MetricInterval: 60 * time.Second,
			LogLevel:       slog.LevelInfo,
		}
	}

	shouldExport := cfg.ForceExport || os.Getenv("GENKIT_ENV") != "dev"
	if shouldExport {
		// Create your telemetry provider's exporters
		traceExporter, err := createYourTraceExporter()
		if err != nil {
			slog.Error("Failed to create trace exporter", "error", err)
			return
		}

		metricExporter, err := createYourMetricExporter()
		if err != nil {
			slog.Error("Failed to create metric exporter", "error", err)
			return
		}

		// Set up traces - direct export or wrapper for custom processing
		spanProcessor := trace.NewBatchSpanProcessor(traceExporter)

		// For custom processing, use wrapper:
		// adjustingExporter := &YourAdjustingTraceExporter{exporter: traceExporter}
		// spanProcessor := trace.NewBatchSpanProcessor(adjustingExporter)
		tp := trace.NewTracerProvider(
			trace.WithSpanProcessor(spanProcessor),
			trace.WithResource(resource.NewWithAttributes(
				semconv.SchemaURL,
				semconv.ServiceName("your-service"),
			)),
		)
		otel.SetTracerProvider(tp)

		// Set up metrics with periodic reader
		r := sdkmetric.NewPeriodicReader(
			metricExporter,
			sdkmetric.WithInterval(cfg.MetricInterval),
		)
		mp := sdkmetric.NewMeterProvider(sdkmetric.WithReader(r))
		otel.SetMeterProvider(mp)

		// Set up logging
		logger := slog.New(YourCustomHandler{
			Options: &slog.HandlerOptions{Level: cfg.LogLevel},
		})
		slog.SetDefault(logger)
	}
}

// [END enablecustom]

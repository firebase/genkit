// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// The googlecloud package supports telemetry (tracing , metrics and logging) using
// Google Cloud services.
package googlecloud

import (
	"context"
	"flag"
	"log/slog"
	"os"
	"runtime"
	"testing"
	"time"

	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"go.opentelemetry.io/otel"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

var projectID = flag.String("project", "", "GCP project ID")

// This test is part of verifying that we can export traces to GCP.
// To verify, run the test, then:
//   - visit the GCP Trace Explorer and look for the "test" trace
//   - visit the Metrics Explorer and look for the "Generic Node - test" metric.
//   - visit the Logging Explorer and look for the genkit_log logName, or run
//     gcloud --project PROJECT_ID logging read 'logName:genkit_log'
func TestGCP(t *testing.T) {
	if *projectID == "" {
		t.Skip("no -project")
	}
	ctx := context.Background()
	t.Run("tracing", func(t *testing.T) {
		tp := sdktrace.NewTracerProvider()
		exp, err := texporter.New(texporter.WithProjectID(*projectID))
		if err != nil {
			t.Fatal(err)
		}
		tp.RegisterSpanProcessor(sdktrace.NewBatchSpanProcessor(exp))
		ctx, span := tp.Tracer("genkit-test").Start(ctx, "test")
		time.Sleep(50 * time.Millisecond)
		span.End()
		if err := tp.Shutdown(ctx); err != nil {
			t.Fatal(err)
		}
	})
	t.Run("metrics", func(t *testing.T) {
		ctx := context.Background()
		if err := setMeterProvider(*projectID, 1*time.Second); err != nil {
			t.Fatal(err)
		}
		c, err := otel.Meter("genkit-test").Int64Counter("test")
		if err != nil {
			t.Fatal(err)
		}
		c.Add(ctx, 100)
		// Allow time to sample and export.
		time.Sleep(2 * time.Second)
	})
	t.Run("logging", func(t *testing.T) {
		if err := setLogHandler(*projectID, slog.LevelInfo); err != nil {
			t.Fatal(err)
		}
		slog.Debug("testing GCP logging",
			"binaryName", os.Args[0],
			"goVersion", runtime.Version())
		// Allow time to export.
		time.Sleep(2 * time.Second)
	})
}

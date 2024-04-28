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

import (
	"context"
	"os"
	"time"

	mexporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/metric"
	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"github.com/google/genkit/go/genkit"
	"go.opentelemetry.io/otel"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

type Options struct {
	// Export to Google Cloud even in the dev environment.
	ForceExport bool

	// The interval for exporting metric data.
	// The default is 60 seconds.
	MetricInterval time.Duration
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
	// TODO(jba): hide PII, perform other adjustments; see AdjustingTraceExporter in the js.
	genkit.RegisterSpanProcessor(sdktrace.NewBatchSpanProcessor(texp))

	return setMeterProvider(projectID, opts.MetricInterval)
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

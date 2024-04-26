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

	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"github.com/google/genkit/go/genkit"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Init initializes all telemetry in this package.
// If forceExport is false, telemetry will not be exported to Google Cloud in the
// dev environment.
func Init(ctx context.Context, projectID string, forceExport bool) error {
	shouldExport := forceExport || os.Getenv("GENKIT_ENV") != "dev"
	if !shouldExport {
		return nil
	}
	// Add a SpanProcessor for tracing.
	e, err := texporter.New(texporter.WithProjectID(projectID))
	if err != nil {
		return err
	}
	// TODO(jba): hide PII, perform other adjustments; see AdjustingTraceExporter in the js.
	genkit.RegisterSpanProcessor(sdktrace.NewBatchSpanProcessor(e))
	return nil
}

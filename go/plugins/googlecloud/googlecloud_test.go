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

// The googlecloud package supports telemetry (tracing , metrics and logging) using
// Google Cloud services.
package googlecloud

import (
	"context"
	"flag"
	"testing"
	"time"

	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

var projectID = flag.String("project", "", "GCP project ID")

// This test is part of verifying that we can export traces to GCP.
// To verify, run the test, then visit the GCP Trace Explorer and look for the "test"
// trace.
func TestGCP(t *testing.T) {
	if *projectID == "" {
		t.Skip("no -project")
	}
	ctx := context.Background()
	tp := sdktrace.NewTracerProvider()
	exp, err := texporter.New(texporter.WithProjectID(*projectID))
	if err != nil {
		t.Fatal(err)
	}
	tp.RegisterSpanProcessor(sdktrace.NewBatchSpanProcessor(exp))
	ctx, span := tp.Tracer("test").Start(ctx, "test")
	time.Sleep(50 * time.Millisecond)
	span.End()
	if err := tp.Shutdown(ctx); err != nil {
		t.Fatal(err)
	}
}

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
	"log/slog"
	"testing"
	"testing/slogtest"

	"cloud.google.com/go/logging"
)

func TestHandler(t *testing.T) {
	var results []map[string]any

	f := func(e logging.Entry) {
		results = append(results, entryToMap(e))
	}

	if err := slogtest.TestHandler(newHandler(slog.LevelInfo, f), func() []map[string]any { return results }); err != nil {
		t.Fatal(err)
	}
}

func entryToMap(e logging.Entry) map[string]any {
	m := map[string]any{}
	if !e.Timestamp.IsZero() {
		m[slog.TimeKey] = e.Timestamp
	}
	m[slog.LevelKey] = e.Severity
	pm := e.Payload.(map[string]any)
	for k, v := range pm {
		m[k] = v
	}
	return m
}

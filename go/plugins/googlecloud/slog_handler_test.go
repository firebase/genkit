// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

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

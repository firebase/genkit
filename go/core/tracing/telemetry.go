// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package tracing

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
)

type TelemetryClient interface {
	Save(ctx context.Context, trace *Data) error
}

// TestOnlyTelemetryClient is a test-only implementation of TelemetryClient that stores traces in memory.
type TestOnlyTelemetryClient struct {
	Traces map[string]*Data
}

// NewTestOnlyTelemetryClient creates a new in-memory telemetry client for testing.
func NewTestOnlyTelemetryClient() *TestOnlyTelemetryClient {
	return &TestOnlyTelemetryClient{
		Traces: make(map[string]*Data),
	}
}

// Save saves the data to an in-memory store.
func (c *TestOnlyTelemetryClient) Save(ctx context.Context, trace *Data) error {
	if trace == nil {
		return fmt.Errorf("trace cannot be nil")
	}
	if trace.TraceID == "" {
		return fmt.Errorf("trace ID cannot be empty")
	}
	if existing, ok := c.Traces[trace.TraceID]; ok {
		for _, span := range trace.Spans {
			existing.Spans[span.SpanID] = span
		}
		if existing.DisplayName == "" {
			existing.DisplayName = trace.DisplayName
		}
	} else {
		c.Traces[trace.TraceID] = trace
	}
	return nil
}

type httpTelemetryClient struct {
	url string
}

// NewHTTPTelemetryClient creates a new telemetry client that sends traces to a telemetry server at the given URL.
func NewHTTPTelemetryClient(url string) *httpTelemetryClient {
	return &httpTelemetryClient{url: url}
}

// Save saves the trace data by making a call to the telemetry server.
func (c *httpTelemetryClient) Save(ctx context.Context, trace *Data) error {
	if c.url == "" {
		return nil
	}
	body, err := json.Marshal(trace)
	if err != nil {
		return fmt.Errorf("failed to marshal trace data: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, "POST", c.url+"/api/traces", bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}
	return nil
}

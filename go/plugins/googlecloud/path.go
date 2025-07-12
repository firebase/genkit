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

package googlecloud

import (
	"fmt"
	"log/slog"
	"time"

	"go.opentelemetry.io/otel/codes"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// PathTelemetry implements telemetry collection for error/failure path tracking
// This matches the JavaScript path.ts implementation
type PathTelemetry struct {
	// Match exact metric names from JS implementation (note: uses feature namespace)
	pathCounter   *MetricCounter   // genkit/feature/path/requests
	pathLatencies *MetricHistogram // genkit/feature/path/latency
	cloudLogger   CloudLogger      // For structured logging to Google Cloud
}

// NewPathTelemetry creates a new path telemetry module with required metrics
func NewPathTelemetry() *PathTelemetry {
	// Note: JavaScript uses "feature" namespace for path metrics
	n := func(name string) string { return internalMetricNamespaceWrap("feature", name) }

	return &PathTelemetry{
		pathCounter: NewMetricCounter(n("path/requests"), MetricCounterOptions{
			Description: "Tracks unique flow paths per flow.",
			Unit:        "1",
		}),
		pathLatencies: NewMetricHistogram(n("path/latency"), MetricHistogramOptions{
			Description: "Latencies per flow path.",
			Unit:        "ms",
		}),
		cloudLogger: NewNoOpCloudLogger(), // Will be set via SetCloudLogger
	}
}

// SetCloudLogger implements the Telemetry interface
func (p *PathTelemetry) SetCloudLogger(logger CloudLogger) {
	p.cloudLogger = logger
}

// Tick processes a span for path telemetry, matching the JavaScript implementation pattern
func (p *PathTelemetry) Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string) {
	attributes := span.Attributes()

	path := extractStringAttribute(attributes, "genkit:path")
	isFailureSource := extractBoolAttribute(attributes, "genkit:isFailureSource")
	state := extractStringAttribute(attributes, "genkit:state")

	// Only process failing, leaf spans (matching JavaScript logic)
	if path == "" || !isFailureSource || state != "error" {
		return
	}

	// Extract session info
	sessionID := extractStringAttribute(attributes, "genkit:sessionId")
	threadName := extractStringAttribute(attributes, "genkit:threadName")

	// Extract error details from span
	errorName := p.extractErrorName(span)
	if errorName == "" {
		errorName = "<unknown>"
	}
	errorMessage := p.extractErrorMessage(span)
	if errorMessage == "" {
		errorMessage = "<unknown>"
	}
	errorStack := p.extractErrorStack(span)

	// Calculate latency
	latencyMs := p.calculateLatencyMs(span)

	// Record metrics
	pathDimensions := map[string]interface{}{
		"featureName":   extractOuterFeatureNameFromPath(path),
		"status":        "failure",
		"error":         errorName,
		"path":          path,
		"source":        "go",
		"sourceVersion": "1.0.0", // TODO: Get actual version
	}
	p.pathCounter.Add(1, pathDimensions)
	p.pathLatencies.Record(latencyMs, pathDimensions)

	// Log structured error
	displayPath := truncatePath(path)
	sharedMetadata := p.createCommonLogAttributes(span, projectID)

	logData := map[string]interface{}{
		"path":          displayPath,
		"qualifiedPath": path,
		"name":          errorName,
		"message":       errorMessage,
		"stack":         errorStack,
		"source":        "go",
		"sourceVersion": "1.0.0",
		"sessionId":     sessionID,
		"threadName":    threadName,
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		logData[k] = v
	}

	// Log as error level (matching JavaScript logStructuredError)
	slog.Error(fmt.Sprintf("Error[%s, %s]", displayPath, errorName), "data", logData)
}

// Helper functions

// calculateLatencyMs calculates the latency in milliseconds from span start/end times
func (p *PathTelemetry) calculateLatencyMs(span sdktrace.ReadOnlySpan) float64 {
	startTime := span.StartTime()
	endTime := span.EndTime()

	if endTime.IsZero() {
		// Span hasn't ended yet, use current time
		endTime = time.Now()
	}

	duration := endTime.Sub(startTime)
	return float64(duration.Nanoseconds()) / 1e6 // Convert to milliseconds
}

// extractErrorName extracts error name from span events and status
func (p *PathTelemetry) extractErrorName(span sdktrace.ReadOnlySpan) string {
	// Check events for error information first
	for _, event := range span.Events() {
		if event.Name == "exception" {
			for _, attr := range event.Attributes {
				if string(attr.Key) == "exception.type" {
					return attr.Value.AsString()
				}
			}
		}
	}

	// Fallback to span status
	if span.Status().Code == codes.Error {
		return span.Status().Description
	}

	return ""
}

// extractErrorMessage extracts error message from span events
func (p *PathTelemetry) extractErrorMessage(span sdktrace.ReadOnlySpan) string {
	for _, event := range span.Events() {
		if event.Name == "exception" {
			for _, attr := range event.Attributes {
				if string(attr.Key) == "exception.message" {
					return attr.Value.AsString()
				}
			}
		}
	}
	return ""
}

// extractErrorStack extracts error stack trace from span events
func (p *PathTelemetry) extractErrorStack(span sdktrace.ReadOnlySpan) string {
	for _, event := range span.Events() {
		if event.Name == "exception" {
			for _, attr := range event.Attributes {
				if string(attr.Key) == "exception.stacktrace" {
					return attr.Value.AsString()
				}
			}
		}
	}
	return ""
}

// createCommonLogAttributes creates common log attributes for correlation with traces
func (p *PathTelemetry) createCommonLogAttributes(span sdktrace.ReadOnlySpan, projectID string) map[string]interface{} {
	spanContext := span.SpanContext()
	return map[string]interface{}{
		"logging.googleapis.com/trace":         fmt.Sprintf("projects/%s/traces/%s", projectID, spanContext.TraceID().String()),
		"logging.googleapis.com/spanId":        spanContext.SpanID().String(),
		"logging.googleapis.com/trace_sampled": spanContext.IsSampled(),
	}
}

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
	"context"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/firebase/genkit/go/internal"
	"go.opentelemetry.io/otel/codes"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"
)

// PathTelemetry implements telemetry collection for error/failure path tracking
type PathTelemetry struct {
	// Note: uses feature namespace for path metrics
	pathCounter   *MetricCounter   // genkit/feature/path/requests
	pathLatencies *MetricHistogram // genkit/feature/path/latency
}

// NewPathTelemetry creates a new path telemetry module with required metrics
func NewPathTelemetry() *PathTelemetry {
	// Note: uses "feature" namespace for path metrics
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
	}
}

// Tick processes a span for path telemetry
func (p *PathTelemetry) Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string) {
	// Get context with span context for trace information
	ctx := trace.ContextWithSpanContext(context.Background(), span.SpanContext())
	attributes := span.Attributes()

	path := extractStringAttribute(attributes, "genkit:path")
	isFailureSource := extractBoolAttribute(attributes, "genkit:isFailureSource")
	state := extractStringAttribute(attributes, "genkit:state")

	// Only process failing, leaf spans
	if path == "" || !isFailureSource || state != "error" {
		return
	}

	// Extract session info
	sessionID := extractStringAttribute(attributes, "genkit:sessionId")
	threadName := extractStringAttribute(attributes, "genkit:threadName")

	// Extract error details from span - align with TypeScript format
	// TypeScript always uses "Error" as the error type/name
	errorType := "Error"

	// Get the actual error message from span status or events
	errorMessage := p.extractErrorMessage(span)
	if errorMessage == "" {
		// Fallback to span status description if no event message
		if span.Status().Code == codes.Error {
			errorMessage = span.Status().Description
		}
		if errorMessage == "" {
			errorMessage = "unknown error"
		}
	}

	errorStack := p.extractErrorStack(span)

	// Calculate latency
	latencyMs := p.calculateLatencyMs(span)

	// Record metrics
	pathDimensions := map[string]interface{}{
		"featureName":   extractOuterFeatureNameFromPath(path),
		"status":        "failure",
		"error":         errorType,
		"path":          path,
		"source":        "go",
		"sourceVersion": internal.Version,
	}

	p.pathCounter.Add(1, pathDimensions)
	p.pathLatencies.Record(latencyMs, pathDimensions)

	// Use full path like TypeScript (preserve substep information)
	// Convert /{flow,t:flow}/{substep,t:flowStep} -> flow > substep
	displayPath := toDisplayPath(path)
	sharedMetadata := createCommonLogAttributes(span, projectID)

	logData := map[string]interface{}{
		"path":          displayPath,
		"qualifiedPath": path,
		"name":          errorType,
		"stack":         errorStack,
		"source":        "go",
		"sourceVersion": internal.Version,
	}

	// Only add session fields if they have values (like TypeScript)
	if sessionID != "" {
		logData["sessionId"] = sessionID
	}
	if threadName != "" {
		logData["threadName"] = threadName
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		logData[k] = v
	}

	// Log as error level - format like TypeScript: [genkit] Error[path, Error] message
	logMessage := fmt.Sprintf("[genkit] Error[%s, %s] %s", displayPath, errorType, errorMessage)
	slog.ErrorContext(ctx, logMessage, MetadataKey, logData)
}

// Helper functions

// extractSimplePathFromQualified extracts simple path name from qualified path
// /{simple-error-test,t:flow} -> simple-error-test
func extractSimplePathFromQualified(qualifiedPath string) string {
	if qualifiedPath == "" {
		return ""
	}

	// Remove leading slash if present
	path := strings.TrimPrefix(qualifiedPath, "/")

	// Find the first brace to get the segment
	if strings.HasPrefix(path, "{") && strings.Contains(path, "}") {
		// Extract content between first { and }
		end := strings.Index(path, "}")
		if end > 1 {
			content := path[1:end]
			// Split by comma and take the first part (the name)
			if parts := strings.Split(content, ","); len(parts) > 0 {
				return parts[0]
			}
		}
	}

	// If not in expected format, return as-is
	return qualifiedPath
}

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
				if string(attr.Key) == "exception.message" {
					return attr.Value.AsString()
				}
			}
		}
	}
	return ""
}

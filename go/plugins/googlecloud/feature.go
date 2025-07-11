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

// FeatureTelemetry implements telemetry collection for top-level feature requests
// This matches the JavaScript feature.ts implementation
type FeatureTelemetry struct {
	// Match exact metric names from JS implementation
	featureCounter   *MetricCounter   // genkit/feature/requests
	featureLatencies *MetricHistogram // genkit/feature/latency
	cloudLogger      CloudLogger      // For structured logging to Google Cloud
}

// NewFeatureTelemetry creates a new feature telemetry module with required metrics
func NewFeatureTelemetry() *FeatureTelemetry {
	// Use the namespace wrapper from metrics.go to match JS naming
	n := func(name string) string { return internalMetricNamespaceWrap("feature", name) }

	return &FeatureTelemetry{
		featureCounter: NewMetricCounter(n("requests"), MetricCounterOptions{
			Description: "Counts calls to genkit features.",
			Unit:        "1",
		}),
		featureLatencies: NewMetricHistogram(n("latency"), MetricHistogramOptions{
			Description: "Latencies when calling Genkit features.",
			Unit:        "ms",
		}),
		cloudLogger: NewNoOpCloudLogger(), // Will be set via SetCloudLogger
	}
}

// SetCloudLogger implements the Telemetry interface
func (f *FeatureTelemetry) SetCloudLogger(logger CloudLogger) {
	f.cloudLogger = logger
}

// Tick processes a span for feature telemetry, matching the JavaScript implementation pattern
func (f *FeatureTelemetry) Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string) {
	attributes := span.Attributes()

	// DEBUG: Log what spans we're seeing
	isRoot := extractBoolAttribute(attributes, "genkit:isRoot")
	subtype := extractStringAttribute(attributes, "genkit:metadata:subtype")
	spanName := extractStringAttribute(attributes, "genkit:name")
	state := extractStringAttribute(attributes, "genkit:state")

	slog.Info("FeatureTelemetry.Tick: Processing span",
		"span_name", span.Name(),
		"isRoot", isRoot,
		"subtype", subtype,
		"genkit:name", spanName,
		"genkit:state", state)

	// Only process root spans - these represent top-level features
	if !isRoot {
		slog.Info("FeatureTelemetry.Tick: Skipping non-root span", "isRoot", isRoot)
		return
	}

	slog.Info("FeatureTelemetry.Tick: Processing root span as feature!", "isRoot", isRoot)

	// Extract key span data
	name := extractStringAttribute(attributes, "genkit:name")
	path := extractStringAttribute(attributes, "genkit:path")
	// state already extracted above for debug logging

	// Calculate latency from span timing
	latencyMs := f.calculateLatencyMs(span)

	// Process based on state
	switch state {
	case "success":
		f.writeFeatureSuccess(name, latencyMs)
	case "error":
		errorName := f.extractErrorName(span)
		if errorName == "" {
			errorName = "<unknown>"
		}
		f.writeFeatureFailure(name, latencyMs, errorName)
	default:
		if state != "" {
			slog.Warn("Unknown feature state", "state", state, "feature", name)
		}
		return
	}

	// Write input/output logs if enabled
	if logInputOutput {
		input := truncate(extractStringAttribute(attributes, "genkit:input"))
		output := truncate(extractStringAttribute(attributes, "genkit:output"))
		sessionID := extractStringAttribute(attributes, "genkit:sessionId")
		threadName := extractStringAttribute(attributes, "genkit:threadName")

		if input != "" {
			f.writeLog(span, "Input", name, path, input, projectID, sessionID, threadName)
		}
		if output != "" {
			f.writeLog(span, "Output", name, path, output, projectID, sessionID, threadName)
		}
	}
}

// writeFeatureSuccess records metrics for successful feature calls
func (f *FeatureTelemetry) writeFeatureSuccess(featureName string, latencyMs float64) {
	dimensions := map[string]interface{}{
		"name":          featureName,
		"status":        "success",
		"source":        "go",
		"sourceVersion": "1.0.0", // TODO: Get actual version
	}

	f.featureCounter.Add(1, dimensions)
	f.featureLatencies.Record(latencyMs, dimensions)
}

// writeFeatureFailure records metrics for failed feature calls
func (f *FeatureTelemetry) writeFeatureFailure(featureName string, latencyMs float64, errorName string) {
	dimensions := map[string]interface{}{
		"name":          featureName,
		"status":        "failure",
		"source":        "go",
		"sourceVersion": "1.0.0", // TODO: Get actual version
		"error":         errorName,
	}

	f.featureCounter.Add(1, dimensions)
	f.featureLatencies.Record(latencyMs, dimensions)
}

// writeLog writes structured logs for feature input/output
func (f *FeatureTelemetry) writeLog(span sdktrace.ReadOnlySpan, tag, featureName, qualifiedPath, content, projectID, sessionID, threadName string) {
	path := truncatePath(qualifiedPath)
	sharedMetadata := f.createCommonLogAttributes(span, projectID)

	logData := map[string]interface{}{
		"path":          path,
		"qualifiedPath": qualifiedPath,
		"featureName":   featureName,
		"sessionId":     sessionID,
		"threadName":    threadName,
		"content":       content,
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		logData[k] = v
	}

	slog.Info(fmt.Sprintf("%s[%s, %s]", tag, path, featureName), "data", logData)
}

// Helper functions

// calculateLatencyMs calculates the latency in milliseconds from span start/end times
func (f *FeatureTelemetry) calculateLatencyMs(span sdktrace.ReadOnlySpan) float64 {
	startTime := span.StartTime()
	endTime := span.EndTime()

	if endTime.IsZero() {
		// Span hasn't ended yet, use current time
		endTime = time.Now()
	}

	duration := endTime.Sub(startTime)
	return float64(duration.Nanoseconds()) / 1e6 // Convert to milliseconds
}

// extractErrorName extracts error information from span, matching JavaScript logic
func (f *FeatureTelemetry) extractErrorName(span sdktrace.ReadOnlySpan) string {
	// Check span status first
	if span.Status().Code == codes.Error {
		return span.Status().Description
	}

	// Check events for error information
	for _, event := range span.Events() {
		if event.Name == "exception" {
			for _, attr := range event.Attributes {
				if string(attr.Key) == "exception.type" {
					return attr.Value.AsString()
				}
			}
		}
	}

	return ""
}

// createCommonLogAttributes creates common log attributes for correlation with traces
func (f *FeatureTelemetry) createCommonLogAttributes(span sdktrace.ReadOnlySpan, projectID string) map[string]interface{} {
	spanContext := span.SpanContext()
	return map[string]interface{}{
		"logging.googleapis.com/trace":         fmt.Sprintf("projects/%s/traces/%s", projectID, spanContext.TraceID().String()),
		"logging.googleapis.com/spanId":        spanContext.SpanID().String(),
		"logging.googleapis.com/trace_sampled": spanContext.IsSampled(),
	}
}

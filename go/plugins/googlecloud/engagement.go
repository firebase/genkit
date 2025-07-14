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
	"regexp"

	"go.opentelemetry.io/otel/attribute"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// EngagementTelemetry implements telemetry collection for user engagement (feedback/acceptance)
type EngagementTelemetry struct {
	feedbackCounter   *MetricCounter // genkit/engagement/feedback
	acceptanceCounter *MetricCounter // genkit/engagement/acceptance
	cloudLogger       CloudLogger    // For structured logging to Google Cloud
}

// NewEngagementTelemetry creates a new engagement telemetry module with required metrics
func NewEngagementTelemetry() *EngagementTelemetry {
	// Use the namespace wrapper from metrics.go
	n := func(name string) string { return internalMetricNamespaceWrap("engagement", name) }

	return &EngagementTelemetry{
		feedbackCounter: NewMetricCounter(n("feedback"), MetricCounterOptions{
			Description: "Counts calls to genkit flows.",
			Unit:        "1",
		}),
		acceptanceCounter: NewMetricCounter(n("acceptance"), MetricCounterOptions{
			Description: "Tracks unique flow paths per flow.",
			Unit:        "1",
		}),
		cloudLogger: NewNoOpCloudLogger(), // Will be set via SetCloudLogger
	}
}

// SetCloudLogger implements the Telemetry interface
func (e *EngagementTelemetry) SetCloudLogger(logger CloudLogger) {
	e.cloudLogger = logger
}

// Tick processes a span for engagement telemetry
func (e *EngagementTelemetry) Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string) {
	attributes := span.Attributes()
	subtype := extractStringAttribute(attributes, "genkit:metadata:subtype")

	switch subtype {
	case "userFeedback":
		e.writeUserFeedback(span, projectID)
	case "userAcceptance":
		e.writeUserAcceptance(span, projectID)
	default:
		if subtype != "" {
			slog.Warn("Unknown user engagement subtype", "subtype", subtype)
		}
	}
}

// writeUserFeedback records metrics and logs for user feedback
func (e *EngagementTelemetry) writeUserFeedback(span sdktrace.ReadOnlySpan, projectID string) {
	attributes := span.Attributes()
	name := e.extractTraceName(attributes)

	// Extract feedback-specific attributes
	feedbackValue := extractStringAttribute(attributes, "genkit:metadata:feedbackValue")
	textFeedback := extractStringAttribute(attributes, "genkit:metadata:textFeedback")
	hasText := textFeedback != ""

	// Record metrics
	dimensions := map[string]interface{}{
		"name":          name,
		"value":         feedbackValue,
		"hasText":       hasText,
		"source":        "go",
		"sourceVersion": "1.0.0", // TODO: Get actual version
	}
	e.feedbackCounter.Add(1, dimensions)

	// Record structured log
	sharedMetadata := e.createCommonLogAttributes(span, projectID)
	logData := map[string]interface{}{
		"feedbackValue": feedbackValue,
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		logData[k] = v
	}

	// Add text feedback if present
	if hasText {
		logData["textFeedback"] = truncate(textFeedback)
	}

	slog.Info(fmt.Sprintf("UserFeedback[%s]", name), "data", logData)
}

// writeUserAcceptance records metrics and logs for user acceptance
func (e *EngagementTelemetry) writeUserAcceptance(span sdktrace.ReadOnlySpan, projectID string) {
	attributes := span.Attributes()
	name := e.extractTraceName(attributes)

	// Extract acceptance-specific attributes
	acceptanceValue := extractStringAttribute(attributes, "genkit:metadata:acceptanceValue")

	// Record metrics
	dimensions := map[string]interface{}{
		"name":          name,
		"value":         acceptanceValue,
		"source":        "go",
		"sourceVersion": "1.0.0", // TODO: Get actual version
	}
	e.acceptanceCounter.Add(1, dimensions)

	// Record structured log
	sharedMetadata := e.createCommonLogAttributes(span, projectID)
	logData := map[string]interface{}{
		"acceptanceValue": acceptanceValue,
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		logData[k] = v
	}

	slog.Info(fmt.Sprintf("UserAcceptance[%s]", name), "data", logData)
}

// Helper functions

// extractTraceName extracts trace name from path using regex
func (e *EngagementTelemetry) extractTraceName(attributes []attribute.KeyValue) string {
	path := extractStringAttribute(attributes, "genkit:path")
	if path == "" || path == "<unknown>" {
		return "<unknown>"
	}

	// Extract feature name from path using regex pattern: /{(.+)}+
	re := regexp.MustCompile(`/{(.+)}+`)
	matches := re.FindStringSubmatch(path)
	if len(matches) > 1 {
		return matches[1]
	}

	return "<unknown>"
}

// createCommonLogAttributes creates common log attributes for correlation with traces
func (e *EngagementTelemetry) createCommonLogAttributes(span sdktrace.ReadOnlySpan, projectID string) map[string]interface{} {
	spanContext := span.SpanContext()
	return map[string]interface{}{
		"logging.googleapis.com/trace":         fmt.Sprintf("projects/%s/traces/%s", projectID, spanContext.TraceID().String()),
		"logging.googleapis.com/spanId":        spanContext.SpanID().String(),
		"logging.googleapis.com/trace_sampled": spanContext.IsSampled(),
	}
}

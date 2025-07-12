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

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// ActionTelemetry implements telemetry collection for action input/output logging
// This matches the JavaScript action.ts implementation
type ActionTelemetry struct {
	// Note: Unlike generate and feature telemetry, action telemetry only does logging, no metrics
	cloudLogger CloudLogger // For structured logging to Google Cloud
}

// NewActionTelemetry creates a new action telemetry module
func NewActionTelemetry() *ActionTelemetry {
	return &ActionTelemetry{
		cloudLogger: NewNoOpCloudLogger(), // Will be set via SetCloudLogger
	}
}

// SetCloudLogger implements the Telemetry interface
func (a *ActionTelemetry) SetCloudLogger(logger CloudLogger) {
	a.cloudLogger = logger
}

// Tick processes a span for action telemetry, matching the JavaScript implementation pattern
func (a *ActionTelemetry) Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string) {
	// Action telemetry only runs if input/output logging is enabled
	if !logInputOutput {
		return
	}

	attributes := span.Attributes()
	actionName := extractStringAttribute(attributes, "genkit:name")
	if actionName == "" {
		actionName = "<unknown>"
	}

	subtype := extractStringAttribute(attributes, "genkit:metadata:subtype")

	// Only process tool actions or generate actions (matching JavaScript logic)
	if subtype == "tool" || actionName == "generate" {
		path := extractStringAttribute(attributes, "genkit:path")
		if path == "" {
			path = "<unknown>"
		}

		input := truncate(extractStringAttribute(attributes, "genkit:input"))
		output := truncate(extractStringAttribute(attributes, "genkit:output"))
		sessionID := extractStringAttribute(attributes, "genkit:sessionId")
		threadName := extractStringAttribute(attributes, "genkit:threadName")

		// Extract feature name from path, fallback to action name
		featureName := extractOuterFeatureNameFromPath(path)
		if featureName == "" || featureName == "<unknown>" {
			featureName = actionName
		}

		// Write input log if we have input data
		if input != "" {
			a.writeLog(span, "Input", featureName, path, input, projectID, sessionID, threadName)
		}

		// Write output log if we have output data
		if output != "" {
			a.writeLog(span, "Output", featureName, path, output, projectID, sessionID, threadName)
		}
	}
}

// writeLog writes structured logs for action input/output
func (a *ActionTelemetry) writeLog(span sdktrace.ReadOnlySpan, tag, featureName, qualifiedPath, content, projectID, sessionID, threadName string) {
	path := truncatePath(qualifiedPath)
	sharedMetadata := a.createCommonLogAttributes(span, projectID)

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

// createCommonLogAttributes creates common log attributes for correlation with traces
func (a *ActionTelemetry) createCommonLogAttributes(span sdktrace.ReadOnlySpan, projectID string) map[string]interface{} {
	spanContext := span.SpanContext()
	return map[string]interface{}{
		"logging.googleapis.com/trace":         fmt.Sprintf("projects/%s/traces/%s", projectID, spanContext.TraceID().String()),
		"logging.googleapis.com/spanId":        spanContext.SpanID().String(),
		"logging.googleapis.com/trace_sampled": spanContext.IsSampled(),
	}
}

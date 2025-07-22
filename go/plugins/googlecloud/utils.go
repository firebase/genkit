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
	"strings"
	"time"

	"go.opentelemetry.io/otel/attribute"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

const (
	MaxLogContentLength = 128000 // 128,000 characters
	MaxPathLength       = 4096   // 4,096 characters for paths
)

// createCommonLogAttributes creates common log attributes for correlation with traces
// This function is shared across all telemetry modules to ensure consistent trace correlation
func createCommonLogAttributes(span sdktrace.ReadOnlySpan, projectID string) map[string]interface{} {
	spanContext := span.SpanContext()
	traceSampled := "0"
	if spanContext.IsSampled() {
		traceSampled = "1"
	}
	return map[string]interface{}{
		"logging.googleapis.com/trace":         fmt.Sprintf("projects/%s/traces/%s", projectID, spanContext.TraceID().String()),
		"logging.googleapis.com/spanId":        spanContext.SpanID().String(),
		"logging.googleapis.com/trace_sampled": traceSampled,
	}
}

// extractStringAttribute safely extracts a string attribute from span attributes
func extractStringAttribute(attrs []attribute.KeyValue, key string) string {
	for _, attr := range attrs {
		if string(attr.Key) == key {
			return attr.Value.AsString()
		}
	}
	return ""
}

// extractBoolAttribute safely extracts a boolean attribute from span attributes
func extractBoolAttribute(attrs []attribute.KeyValue, key string) bool {
	for _, attr := range attrs {
		if string(attr.Key) == key {
			return attr.Value.AsBool()
		}
	}
	return false
}

// extractInt64Attribute safely extracts an int64 attribute from span attributes
func extractInt64Attribute(attrs []attribute.KeyValue, key string) int64 {
	for _, attr := range attrs {
		if string(attr.Key) == key {
			return attr.Value.AsInt64()
		}
	}
	return 0
}

// truncate limits string length to maxLen characters
func truncate(text string, limit ...int) string {
	maxLen := MaxLogContentLength
	if len(limit) > 0 && limit[0] > 0 {
		maxLen = limit[0]
	}

	if text == "" || len(text) <= maxLen {
		return text
	}

	return text[:maxLen]
}

// truncatePath limits path length
func truncatePath(path string) string {
	return truncate(path, MaxPathLength)
}

// Permission and error detection utilities

// requestDenied checks if an error is a permission denied error
func requestDenied(err error) bool {
	if grpcErr, ok := status.FromError(err); ok {
		return grpcErr.Code() == codes.PermissionDenied
	}
	return false
}

// loggingDenied checks if an error is specifically related to logging permissions
func loggingDenied(err error) bool {
	return requestDenied(err)
	// Note: Unlike TypeScript, Go gRPC errors don't include statusDetails
	// with granular permission information, so we use the general permission check
}

// Help text generation functions

// permissionDeniedHelpText generates helpful text for permission errors
func permissionDeniedHelpText(role, projectID string) string {
	return fmt.Sprintf(`Add the role '%s' to your Service Account in the IAM & Admin page on the Google Cloud console, or use the following command:

gcloud projects add-iam-policy-binding %s \
    --member=serviceAccount:${SERVICE_ACCOUNT_EMAIL} \
    --role=%s

For more information, see: https://cloud.google.com/docs/authentication/getting-started`, role, projectID, role)
}

// loggingDeniedHelpText provides specific help for logging permission errors
func loggingDeniedHelpText(projectID string) string {
	return permissionDeniedHelpText("roles/logging.logWriter", projectID)
}

// Utility functions for path parsing

// extractOuterFeatureNameFromPath extracts the first feature name from a path
// e.g. for /{myFlow,t:flow}/{myStep,t:flowStep}/{googleai/gemini-pro,t:action,s:model}
// returns "myFlow"
func extractOuterFeatureNameFromPath(path string) string {
	if path == "" || path == "<unknown>" {
		return "<unknown>"
	}

	// Simple path parsing - extract feature name from genkit path format
	if len(path) > 0 && path[0] == '/' {
		parts := strings.Split(path[1:], "/")
		if len(parts) > 0 {
			first := parts[0]
			// Extract name from {name,t:type} format
			if strings.HasPrefix(first, "{") && strings.Contains(first, ",") {
				end := strings.Index(first, ",")
				if end > 1 {
					return first[1:end]
				}
			}
		}
	}

	return "<unknown>"
}

// Functional option helpers for common configurations

// WithForceExport sets the ForceExport flag
func WithForceExport(forceExport bool) Option {
	return func(c *TelemetryConfig) {
		c.ForceExport = forceExport
	}
}

// WithLogLevel sets the log level
func WithLogLevel(level slog.Level) Option {
	return func(c *TelemetryConfig) {
		c.LogLevel = level
	}
}

// WithExportInputAndOutput sets whether to export input/output (matches JS exportInputAndOutput)
func WithExportInputAndOutput(enabled bool) Option {
	return func(c *TelemetryConfig) {
		c.ExportInputAndOutput = enabled
	}
}

// WithMetricInterval sets the metric collection interval
func WithMetricInterval(interval time.Duration) Option {
	return func(c *TelemetryConfig) {
		c.MetricInterval = interval
	}
}

// WithMetricTimeout sets the metric timeout in milliseconds
func WithMetricTimeout(timeoutMs int) Option {
	return func(c *TelemetryConfig) {
		c.MetricTimeoutMillis = timeoutMs
	}
}

// WithBufferSize sets the buffer size
func WithBufferSize(size int) Option {
	return func(c *TelemetryConfig) {
		c.BufferSize = size
	}
}

// WithExport sets whether to export telemetry
func WithExport(export bool) Option {
	return func(c *TelemetryConfig) {
		c.Export = export
	}
}

// Module-specific options

// WithEnableGenerate sets whether to enable generate module telemetry
func WithEnableGenerate(enabled bool) Option {
	return func(c *TelemetryConfig) {
		c.EnableGenerate = enabled
	}
}

// WithEnableFeature sets whether to enable feature module telemetry
func WithEnableFeature(enabled bool) Option {
	return func(c *TelemetryConfig) {
		c.EnableFeature = enabled
	}
}

// WithEnableAction sets whether to enable action module telemetry
func WithEnableAction(enabled bool) Option {
	return func(c *TelemetryConfig) {
		c.EnableAction = enabled
	}
}

// WithEnableEngagement sets whether to enable engagement module telemetry
func WithEnableEngagement(enabled bool) Option {
	return func(c *TelemetryConfig) {
		c.EnableEngagement = enabled
	}
}

// WithEnablePath sets whether to enable path module telemetry
func WithEnablePath(enabled bool) Option {
	return func(c *TelemetryConfig) {
		c.EnablePath = enabled
	}
}

// Convenience options for common configurations

// WithDisableMetrics disables metric collection modules
func WithDisableMetrics() Option {
	return func(c *TelemetryConfig) {
		c.EnableGenerate = false
		c.EnableFeature = false
	}
}

// WithDisableAllTelemetry disables all telemetry modules
func WithDisableAllTelemetry() Option {
	return func(c *TelemetryConfig) {
		c.EnableGenerate = false
		c.EnableFeature = false
		c.EnableAction = false
		c.EnableEngagement = false
		c.EnablePath = false
	}
}

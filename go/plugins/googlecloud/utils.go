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
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"runtime"
	"strings"
	"time"

	"go.opentelemetry.io/otel/attribute"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Enhanced truncation with proper UTF-8 handling
func safeTruncate(s string, maxLen ...int) string {
	max := MaxLogContentLength // Default to log content length like JS
	if len(maxLen) > 0 && maxLen[0] > 0 {
		max = maxLen[0]
	}

	if len(s) <= max {
		return s
	}

	// Ensure we don't cut in the middle of a UTF-8 character
	truncated := s[:max]
	for len(truncated) > 0 && !isValidUTF8Start(truncated[len(truncated)-1]) {
		truncated = truncated[:len(truncated)-1]
	}

	return truncated
}

func isValidUTF8Start(b byte) bool {
	return b&0x80 == 0 || b&0xC0 == 0xC0
}

func safeExtractOuterFeatureNameFromPath(path string) string {
	if path == "" {
		return ErrUnknown
	}

	parts := strings.Split(path, "/")
	if len(parts) == 0 {
		return ErrUnknown
	}

	// Return the first meaningful part
	for _, part := range parts {
		if part != "" {
			return safeTruncate(part)
		}
	}

	return ErrUnknown
}

// ErrorDetails provides structured error information
type ErrorDetails struct {
	HasError bool   `json:"has_error"`
	Name     string `json:"name"`
	Message  string `json:"message"`
	Stack    string `json:"stack"`
}

// Enhanced log attributes creation with validation
func createEnhancedLogAttributes(span sdktrace.ReadOnlySpan, projectID string) map[string]interface{} {
	if projectID == "" {
		projectID = DefaultProjection
	}

	spanContext := span.SpanContext()

	attrs := map[string]interface{}{
		"logging.googleapis.com/trace":         fmt.Sprintf("projects/%s/traces/%s", projectID, spanContext.TraceID().String()),
		"logging.googleapis.com/spanId":        spanContext.SpanID().String(),
		"logging.googleapis.com/trace_sampled": spanContext.IsSampled(),
	}

	// Add span timing information
	if !span.StartTime().IsZero() {
		attrs["span_start_time"] = span.StartTime().Unix()
	}
	if !span.EndTime().IsZero() {
		attrs["span_end_time"] = span.EndTime().Unix()
		attrs["span_duration_ms"] = float64(span.EndTime().Sub(span.StartTime()).Nanoseconds()) / 1e6
	}

	return attrs
}

// Enhanced dimensions creation with validation
func createEnhancedDimensions(base map[string]interface{}) map[string]interface{} {
	dims := GetTelemetryDimensions() // Get standard dimensions

	// Add base dimensions
	for k, v := range base {
		if v != nil {
			dims[k] = v
		}
	}

	return dims
}

// Performance utilities
func calculateLatencyMs(start, end time.Time) float64 {
	if start.IsZero() {
		return 0
	}

	endTime := end
	if endTime.IsZero() {
		endTime = time.Now()
	}

	if endTime.Before(start) {
		slog.Warn("End time is before start time", "start", start, "end", endTime)
		return 0
	}

	duration := endTime.Sub(start)
	return float64(duration.Nanoseconds()) / 1e6
}

// Validation utilities
func validateProjectID(projectID string) error {
	if projectID == "" {
		return fmt.Errorf(ErrMissingProjectID)
	}

	// Basic GCP project ID validation
	if len(projectID) < 6 || len(projectID) > 30 {
		return fmt.Errorf("project ID must be 6-30 characters")
	}

	// Check for valid characters (simplified)
	for _, r := range projectID {
		if !isValidProjectIDChar(r) {
			return fmt.Errorf("project ID contains invalid character: %c", r)
		}
	}

	return nil
}

func isValidProjectIDChar(r rune) bool {
	return (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-'
}

// Environment detection utilities
func detectEnvironment() string {
	if env := os.Getenv("GENKIT_ENV"); env != "" {
		return env
	}
	if env := os.Getenv("NODE_ENV"); env != "" {
		return env
	}
	if env := os.Getenv("GO_ENV"); env != "" {
		return env
	}
	return "development"
}

func isProductionEnvironment() bool {
	env := detectEnvironment()
	return env == "production" || env == "prod"
}

func shouldExportTelemetry(forceExport bool) bool {
	return forceExport || isProductionEnvironment()
}

// Diagnostic utilities
type DiagnosticInfo struct {
	PluginVersion  string                 `json:"plugin_version"`
	Environment    string                 `json:"environment"`
	GoVersion      string                 `json:"go_version"`
	Platform       string                 `json:"platform"`
	ProjectID      string                 `json:"project_id,omitempty"`
	ModulesEnabled []string               `json:"modules_enabled"`
	Configuration  map[string]interface{} `json:"configuration"`
	RuntimeStats   RuntimeStats           `json:"runtime_stats"`
}

type RuntimeStats struct {
	Goroutines int    `json:"goroutines"`
	MemoryMB   uint64 `json:"memory_mb"`
	GCPauses   int    `json:"gc_pauses"`
}

func CollectDiagnosticInfo(projectID string, modules []string, config map[string]interface{}) DiagnosticInfo {
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	return DiagnosticInfo{
		PluginVersion:  GetSourceVersion(),
		Environment:    detectEnvironment(),
		GoVersion:      runtime.Version(),
		Platform:       fmt.Sprintf("%s/%s", runtime.GOOS, runtime.GOARCH),
		ProjectID:      projectID,
		ModulesEnabled: modules,
		Configuration:  config,
		RuntimeStats: RuntimeStats{
			Goroutines: runtime.NumGoroutine(),
			MemoryMB:   memStats.Alloc / 1024 / 1024,
			GCPauses:   int(memStats.NumGC),
		},
	}
}

// Logging utilities
func logWithContext(ctx context.Context, level slog.Level, msg string, args ...interface{}) {
	logger := slog.Default()

	// Add context values if available
	if ctx != nil {
		if traceID := ctx.Value("trace_id"); traceID != nil {
			args = append(args, "trace_id", traceID)
		}
		if spanID := ctx.Value("span_id"); spanID != nil {
			args = append(args, "span_id", spanID)
		}
	}

	logger.Log(ctx, level, msg, args...)
}

// Debugging utilities
func DebugSpanAttributes(span sdktrace.ReadOnlySpan) {
	if !slog.Default().Enabled(context.Background(), slog.LevelDebug) {
		return
	}

	attrs := span.Attributes()
	attrMap := make(map[string]interface{}, len(attrs))

	for _, attr := range attrs {
		key := string(attr.Key)
		switch attr.Value.Type() {
		case attribute.STRING:
			attrMap[key] = attr.Value.AsString()
		case attribute.BOOL:
			attrMap[key] = attr.Value.AsBool()
		case attribute.INT64:
			attrMap[key] = attr.Value.AsInt64()
		case attribute.FLOAT64:
			attrMap[key] = attr.Value.AsFloat64()
		default:
			attrMap[key] = attr.Value.AsInterface()
		}
	}

	slog.Debug("Span attributes debug",
		"span_name", span.Name(),
		"span_kind", span.SpanKind().String(),
		"attributes", attrMap,
	)
}

// Content processing utilities
func processPartContent(part *Part) string {
	if part == nil {
		return ""
	}

	if part.Text != "" {
		return safeTruncate(part.Text, MaxLogContentLength)
	}

	if part.Data != nil {
		if data, err := json.Marshal(part.Data); err == nil {
			return safeTruncate(string(data), MaxLogContentLength)
		}
	}

	// Handle other part types...
	return "<content unavailable>"
}

// Feature flag utilities (for future use)
type FeatureFlags struct {
	EnableDetailedLogging bool `json:"enable_detailed_logging"`
	EnableMetricsDebug    bool `json:"enable_metrics_debug"`
	EnablePerformanceMode bool `json:"enable_performance_mode"`
}

func getFeatureFlags() FeatureFlags {
	return FeatureFlags{
		EnableDetailedLogging: os.Getenv("GENKIT_DETAILED_LOGGING") == "true",
		EnableMetricsDebug:    os.Getenv("GENKIT_METRICS_DEBUG") == "true",
		EnablePerformanceMode: os.Getenv("GENKIT_PERFORMANCE_MODE") == "true",
	}
}

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
	"log/slog"
	"time"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"golang.org/x/oauth2/google"
)

// Telemetry interface that all telemetry modules implement
type Telemetry interface {
	Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string)
}

// SharedDimensions contains common metric dimensions used across telemetry modules
type SharedDimensions struct {
	FeatureName   string
	Path          string
	Status        string
	Source        string
	SourceVersion string
}

// PluginConfig represents the main plugin configuration with essential fields and nested config
type PluginConfig struct {
	ProjectID   string
	Credentials *google.Credentials
	Config      *TelemetryConfig
}

// TelemetryConfig represents all configurable telemetry settings with concrete values
type TelemetryConfig struct {
	// Core settings
	ForceExport bool

	// Logging settings
	ExportInputAndOutput bool
	LogLevel             slog.Level

	// Performance settings - Environment-aware defaults
	MetricInterval      time.Duration
	MetricTimeoutMillis int
	BufferSize          int

	// Export settings - Environment-aware defaults
	Export bool
}

// GoogleCloudTelemetryOptions provides simple struct-based configuration for Google Cloud telemetry.
// This mirrors the Firebase plugin's approach for consistency while offering the same comprehensive
// observability. For advanced use cases requiring fine-grained module control, use functional options.
type GoogleCloudTelemetryOptions struct {
	// ProjectID is the Google Cloud project ID.
	// If empty, will be auto-detected from environment.
	ProjectID string

	// ForceExport forces telemetry export even in development environment.
	// Defaults to false (only exports in production unless forced).
	ForceExport bool

	// ExportInputAndOutput includes AI model input/output in telemetry traces.
	// Defaults to false for privacy (only metadata is exported).
	ExportInputAndOutput bool
}

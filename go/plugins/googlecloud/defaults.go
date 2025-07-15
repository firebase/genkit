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
	"os"
	"time"

	"golang.org/x/oauth2/google"
)

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

	// Module selection - All enabled by default for comprehensive observability
	EnableGenerate   bool
	EnableFeature    bool
	EnableAction     bool
	EnableEngagement bool
	EnablePath       bool

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

// Option is a function that modifies TelemetryConfig
type Option func(*TelemetryConfig)

// GetCurrentEnv returns the current environment (dev or prod)
func GetCurrentEnv() string {
	env := os.Getenv("GENKIT_ENV")
	if env == "" {
		return "prod"
	}
	return env
}

// IsDevEnv returns true if we're in development environment
// Matches TypeScript's isDevEnv() function
func IsDevEnv() bool {
	return GetCurrentEnv() == "dev"
}

// GetDefaults automatically switches between dev and prod defaults based on environment
// Matches TypeScript's PluginConfigs.defaults() function
func GetDefaults(projectID string, opts ...Option) *PluginConfig {
	if IsDevEnv() {
		return GetDevelopmentDefaults(projectID, opts...)
	}
	return GetProductionDefaults(projectID, opts...)
}

// GetDevelopmentDefaults provides development-specific defaults
// Matches TypeScript's PluginConfigs.developmentDefaults() function
func GetDevelopmentDefaults(projectID string, opts ...Option) *PluginConfig {
	config := &TelemetryConfig{
		// Core settings
		ForceExport: false,

		// Enable all modules by default for comprehensive observability
		EnableGenerate:   true,
		EnableFeature:    true,
		EnableAction:     true,
		EnableEngagement: true,
		EnablePath:       true,

		// Logging settings
		ExportInputAndOutput: true,
		LogLevel:             slog.LevelDebug, // More verbose for development

		// Performance settings - Fast for development
		MetricInterval:      5 * time.Second, // Fast for dev (matches TypeScript 5_000ms)
		MetricTimeoutMillis: 5000,            // Fast for dev (matches TypeScript 5_000ms)
		BufferSize:          100,             // Small buffer for dev

		// Export settings - Don't export in dev by default
		Export: false, // Don't export in dev (matches TypeScript export: false)
	}

	// Apply functional options
	for _, opt := range opts {
		opt(config)
	}

	return &PluginConfig{
		ProjectID: projectID,
		Config:    config,
	}
}

// GetProductionDefaults provides production-specific defaults
// Matches TypeScript's PluginConfigs.productionDefaults() function
func GetProductionDefaults(projectID string, opts ...Option) *PluginConfig {
	config := &TelemetryConfig{
		// Core settings
		ForceExport: false,

		// Enable all modules by default for comprehensive observability
		EnableGenerate:   true,
		EnableFeature:    true,
		EnableAction:     true,
		EnableEngagement: true,
		EnablePath:       true,

		// Logging settings
		ExportInputAndOutput: true,
		LogLevel:             slog.LevelInfo, // Less verbose for production

		// Performance settings - Slower for production
		MetricInterval:      300 * time.Second, // Slower for prod (matches TypeScript 300_000ms)
		MetricTimeoutMillis: 300000,            // Slower for prod (matches TypeScript 300_000ms)
		BufferSize:          1000,              // Larger buffer for prod

		// Export settings - Always export in production
		Export: true, // Always export in prod (matches TypeScript export: true)
	}

	// Apply functional options
	for _, opt := range opts {
		opt(config)
	}

	return &PluginConfig{
		ProjectID: projectID,
		Config:    config,
	}
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

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
)

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

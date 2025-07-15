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
	"testing"
	"time"
)

func TestEnvironmentDetection(t *testing.T) {
	// Test default environment (prod)
	os.Unsetenv("GENKIT_ENV")
	if IsDevEnv() {
		t.Error("Expected prod environment when GENKIT_ENV is not set")
	}
	if GetCurrentEnv() != "prod" {
		t.Errorf("Expected 'prod', got '%s'", GetCurrentEnv())
	}

	// Test dev environment
	os.Setenv("GENKIT_ENV", "dev")
	if !IsDevEnv() {
		t.Error("Expected dev environment when GENKIT_ENV=dev")
	}
	if GetCurrentEnv() != "dev" {
		t.Errorf("Expected 'dev', got '%s'", GetCurrentEnv())
	}

	// Test custom environment (should not be dev)
	os.Setenv("GENKIT_ENV", "staging")
	if IsDevEnv() {
		t.Error("Expected non-dev environment when GENKIT_ENV=staging")
	}
	if GetCurrentEnv() != "staging" {
		t.Errorf("Expected 'staging', got '%s'", GetCurrentEnv())
	}

	// Clean up
	os.Unsetenv("GENKIT_ENV")
}

func TestDevelopmentDefaults(t *testing.T) {
	// Set dev environment
	os.Setenv("GENKIT_ENV", "dev")
	defer os.Unsetenv("GENKIT_ENV")

	defaults := GetDevelopmentDefaults("test-project")

	// Test development-specific values
	if defaults.Config.MetricInterval != 5*time.Second {
		t.Errorf("Expected 5s metric interval for dev, got %v", defaults.Config.MetricInterval)
	}
	if defaults.Config.MetricTimeoutMillis != 5000 {
		t.Errorf("Expected 5000ms timeout for dev, got %d", defaults.Config.MetricTimeoutMillis)
	}
	if defaults.Config.LogLevel != slog.LevelDebug {
		t.Errorf("Expected debug log level for dev, got %v", defaults.Config.LogLevel)
	}
	if defaults.Config.Export {
		t.Error("Expected export=false for dev")
	}
	if defaults.Config.BufferSize != 100 {
		t.Errorf("Expected buffer size 100 for dev, got %d", defaults.Config.BufferSize)
	}

	// Test that all telemetry modules are enabled
	if !defaults.Config.EnableGenerate || !defaults.Config.EnableFeature || !defaults.Config.EnableAction ||
		!defaults.Config.EnableEngagement || !defaults.Config.EnablePath {
		t.Error("Expected all telemetry modules to be enabled in dev")
	}
}

func TestProductionDefaults(t *testing.T) {
	// Set prod environment
	os.Setenv("GENKIT_ENV", "prod")
	defer os.Unsetenv("GENKIT_ENV")

	defaults := GetProductionDefaults("test-project")

	// Test production-specific values
	if defaults.Config.MetricInterval != 300*time.Second {
		t.Errorf("Expected 300s metric interval for prod, got %v", defaults.Config.MetricInterval)
	}
	if defaults.Config.MetricTimeoutMillis != 300000 {
		t.Errorf("Expected 300000ms timeout for prod, got %d", defaults.Config.MetricTimeoutMillis)
	}
	if defaults.Config.LogLevel != slog.LevelInfo {
		t.Errorf("Expected info log level for prod, got %v", defaults.Config.LogLevel)
	}
	if !defaults.Config.Export {
		t.Error("Expected export=true for prod")
	}
	if defaults.Config.BufferSize != 1000 {
		t.Errorf("Expected buffer size 1000 for prod, got %d", defaults.Config.BufferSize)
	}

	// Test that all telemetry modules are enabled
	if !defaults.Config.EnableGenerate || !defaults.Config.EnableFeature || !defaults.Config.EnableAction ||
		!defaults.Config.EnableEngagement || !defaults.Config.EnablePath {
		t.Error("Expected all telemetry modules to be enabled in prod")
	}
}

func TestEnvironmentAwareDefaults(t *testing.T) {
	// Test dev environment defaults
	os.Setenv("GENKIT_ENV", "dev")
	devDefaults := GetDefaults("test-project")
	if devDefaults.Config.MetricInterval != 5*time.Second {
		t.Errorf("Expected dev defaults when GENKIT_ENV=dev, got %v", devDefaults.Config.MetricInterval)
	}
	if devDefaults.Config.Export {
		t.Error("Expected export=false for dev defaults")
	}

	// Test prod environment defaults
	os.Setenv("GENKIT_ENV", "prod")
	prodDefaults := GetDefaults("test-project")
	if prodDefaults.Config.MetricInterval != 300*time.Second {
		t.Errorf("Expected prod defaults when GENKIT_ENV=prod, got %v", prodDefaults.Config.MetricInterval)
	}
	if !prodDefaults.Config.Export {
		t.Error("Expected export=true for prod defaults")
	}

	// Clean up
	os.Unsetenv("GENKIT_ENV")
}

func TestUserOverrides(t *testing.T) {
	// Test overriding metric interval
	defaults := GetDefaults("test-project", WithMetricInterval(30*time.Second))
	if defaults.Config.MetricInterval != 30*time.Second {
		t.Errorf("Expected overridden metric interval 30s, got %v", defaults.Config.MetricInterval)
	}

	// Test overriding log level
	defaults = GetDefaults("test-project", WithLogLevel(slog.LevelWarn))
	if defaults.Config.LogLevel != slog.LevelWarn {
		t.Errorf("Expected overridden log level warn, got %v", defaults.Config.LogLevel)
	}

	// Test overriding module enablement
	defaults = GetDefaults("test-project", WithEnableGenerate(false))
	if defaults.Config.EnableGenerate {
		t.Error("Expected generate module to be disabled")
	}
}

func TestHelperFunctions(t *testing.T) {
	// Test WithForceExport
	config := GetDefaults("test-project", WithForceExport(true))
	if !config.Config.ForceExport {
		t.Error("WithForceExport helper function failed")
	}

	// Test WithLogLevel
	config = GetDefaults("test-project", WithLogLevel(slog.LevelError))
	if config.Config.LogLevel != slog.LevelError {
		t.Error("WithLogLevel helper function failed")
	}

	// Test WithMetricInterval
	config = GetDefaults("test-project", WithMetricInterval(45*time.Second))
	if config.Config.MetricInterval != 45*time.Second {
		t.Error("WithMetricInterval helper function failed")
	}

	// Test WithDisableMetrics
	config = GetDefaults("test-project", WithDisableMetrics())
	if config.Config.EnableGenerate || config.Config.EnableFeature {
		t.Error("WithDisableMetrics helper function failed")
	}

	// Test WithDisableAllTelemetry
	config = GetDefaults("test-project", WithDisableAllTelemetry())
	if config.Config.EnableGenerate || config.Config.EnableFeature ||
		config.Config.EnableAction || config.Config.EnableEngagement ||
		config.Config.EnablePath {
		t.Error("WithDisableAllTelemetry helper function failed")
	}
}

func TestNewWithEnvironmentDefaults(t *testing.T) {
	// Test dev environment
	os.Setenv("GENKIT_ENV", "dev")
	plugin := NewWithProjectID("test-project")
	if plugin.Config.Config.MetricInterval != 5*time.Second {
		t.Errorf("Expected dev defaults in NewWithProjectID(), got %v", plugin.Config.Config.MetricInterval)
	}
	if plugin.Config.Config.LogLevel != slog.LevelDebug {
		t.Errorf("Expected debug log level in dev, got %v", plugin.Config.Config.LogLevel)
	}

	// Test prod environment
	os.Setenv("GENKIT_ENV", "prod")
	plugin = NewWithProjectID("test-project")
	if plugin.Config.Config.MetricInterval != 300*time.Second {
		t.Errorf("Expected prod defaults in NewWithProjectID(), got %v", plugin.Config.Config.MetricInterval)
	}
	if plugin.Config.Config.LogLevel != slog.LevelInfo {
		t.Errorf("Expected info log level in prod, got %v", plugin.Config.Config.LogLevel)
	}

	// Test New() with auto-detection (will fail without valid credentials in test)
	os.Setenv("GENKIT_ENV", "dev")
	_, err := New()
	if err == nil {
		t.Error("Expected error when no credentials are available in test environment")
	} else if !contains(err.Error(), "project ID could not be determined") {
		t.Errorf("Expected credential error, got: %v", err)
	}

	// Test NewWithProjectID directly
	plugin = NewWithProjectID("test-project")
	if plugin == nil {
		t.Error("Expected valid plugin from NewWithProjectID")
	}
	if plugin.Config.ProjectID != "test-project" {
		t.Errorf("Expected project ID 'test-project', got %v", plugin.Config.ProjectID)
	}

	// Clean up
	os.Unsetenv("GENKIT_ENV")
}

func TestCredentialDetection(t *testing.T) {
	// Test dev environment
	os.Setenv("GENKIT_ENV", "dev")
	plugin := NewWithProjectID("test-project")
	if plugin.Config.Config.MetricInterval != 5*time.Second {
		t.Errorf("Expected dev defaults in NewWithProjectID(), got %v", plugin.Config.Config.MetricInterval)
	}
	if plugin.Config.Config.LogLevel != slog.LevelDebug {
		t.Errorf("Expected debug log level in dev, got %v", plugin.Config.Config.LogLevel)
	}

	// Test prod environment
	os.Setenv("GENKIT_ENV", "prod")
	plugin = NewWithProjectID("test-project")
	if plugin.Config.Config.MetricInterval != 300*time.Second {
		t.Errorf("Expected prod defaults in NewWithProjectID(), got %v", plugin.Config.Config.MetricInterval)
	}
	if plugin.Config.Config.LogLevel != slog.LevelInfo {
		t.Errorf("Expected info log level in prod, got %v", plugin.Config.Config.LogLevel)
	}

	// Test New() with auto-detection (will fail without valid credentials in test)
	os.Setenv("GENKIT_ENV", "dev")
	_, err := New()
	if err == nil {
		t.Error("Expected error when no credentials are available in test environment")
	} else if !contains(err.Error(), "project ID could not be determined") {
		t.Errorf("Expected credential error, got: %v", err)
	}

	// Test NewWithProjectID with custom options
	plugin = NewWithProjectID("test-project", WithLogLevel(slog.LevelWarn))
	if plugin.Config.ProjectID != "test-project" {
		t.Errorf("Expected project ID 'test-project', got %v", plugin.Config.ProjectID)
	}
	if plugin.Config.Config.LogLevel != slog.LevelWarn {
		t.Errorf("Expected log level warn, got %v", plugin.Config.Config.LogLevel)
	}

	// Clean up
	os.Unsetenv("GENKIT_ENV")
}

// Helper function to check if string contains substring
func contains(s, substr string) bool {
	return len(s) >= len(substr) && s[:len(substr)] == substr ||
		(len(s) > len(substr) && s[1:len(substr)+1] == substr) ||
		(len(s) > len(substr) && s[len(s)-len(substr):] == substr)
}

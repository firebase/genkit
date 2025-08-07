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
	testCases := []struct {
		env      string
		isDev    bool
		expected string
	}{
		{"", false, "prod"},
		{"dev", true, "dev"},
		{"staging", false, "staging"},
	}

	for _, tc := range testCases {
		os.Setenv("GENKIT_ENV", tc.env)
		if IsDevEnv() != tc.isDev {
			t.Errorf("IsDevEnv() = %v, want %v for env=%q", IsDevEnv(), tc.isDev, tc.env)
		}
		if got := GetCurrentEnv(); got != tc.expected {
			t.Errorf("GetCurrentEnv() = %q, want %q", got, tc.expected)
		}
	}

	os.Unsetenv("GENKIT_ENV")
}

func TestDevelopmentDefaults(t *testing.T) {
	os.Setenv("GENKIT_ENV", "dev")
	defer os.Unsetenv("GENKIT_ENV")

	cfg := GetDevelopmentDefaults("test-project").Config

	// Verify dev config values
	expected := &TelemetryConfig{
		MetricInterval:      5 * time.Second,
		MetricTimeoutMillis: 5000,
		LogLevel:            slog.LevelDebug,
		Export:              false,
		BufferSize:          100,
	}

	// Check individual fields since we removed module configuration fields
	if cfg.MetricInterval != expected.MetricInterval {
		t.Errorf("MetricInterval: got %v, expected %v", cfg.MetricInterval, expected.MetricInterval)
	}
	if cfg.MetricTimeoutMillis != expected.MetricTimeoutMillis {
		t.Errorf("MetricTimeoutMillis: got %v, expected %v", cfg.MetricTimeoutMillis, expected.MetricTimeoutMillis)
	}
	if cfg.LogLevel != expected.LogLevel {
		t.Errorf("LogLevel: got %v, expected %v", cfg.LogLevel, expected.LogLevel)
	}
	if cfg.Export != expected.Export {
		t.Errorf("Export: got %v, expected %v", cfg.Export, expected.Export)
	}
	if cfg.BufferSize != expected.BufferSize {
		t.Errorf("BufferSize: got %v, expected %v", cfg.BufferSize, expected.BufferSize)
	}
}

func TestProductionDefaults(t *testing.T) {
	testCases := []string{"staging", "prod", "anyotherenvironment"}

	for _, env := range testCases {
		t.Run(env, func(t *testing.T) {
			os.Setenv("GENKIT_ENV", env)
			defer os.Unsetenv("GENKIT_ENV")

			cfg := GetProductionDefaults("test-project").Config

			expected := &TelemetryConfig{
				MetricInterval:      300 * time.Second,
				MetricTimeoutMillis: 300000,
				LogLevel:            slog.LevelInfo,
				Export:              true,
				BufferSize:          1000,
			}

			// Check individual fields since we removed module configuration fields
			if cfg.MetricInterval != expected.MetricInterval {
				t.Errorf("%s MetricInterval: got %v, expected %v", env, cfg.MetricInterval, expected.MetricInterval)
			}
			if cfg.MetricTimeoutMillis != expected.MetricTimeoutMillis {
				t.Errorf("%s MetricTimeoutMillis: got %v, expected %v", env, cfg.MetricTimeoutMillis, expected.MetricTimeoutMillis)
			}
			if cfg.LogLevel != expected.LogLevel {
				t.Errorf("%s LogLevel: got %v, expected %v", env, cfg.LogLevel, expected.LogLevel)
			}
			if cfg.Export != expected.Export {
				t.Errorf("%s Export: got %v, expected %v", env, cfg.Export, expected.Export)
			}
			if cfg.BufferSize != expected.BufferSize {
				t.Errorf("%s BufferSize: got %v, expected %v", env, cfg.BufferSize, expected.BufferSize)
			}
		})
	}
}
func TestEnvironmentAwareDefaults(t *testing.T) {
	testCases := []struct {
		env          string
		wantInterval time.Duration
		wantExport   bool
	}{
		{"dev", 5 * time.Second, false},
		{"prod", 300 * time.Second, true},
	}

	for _, tc := range testCases {
		t.Run(tc.env, func(t *testing.T) {
			os.Setenv("GENKIT_ENV", tc.env)
			defer os.Unsetenv("GENKIT_ENV")

			defaults := GetDefaults("test-project")
			if defaults.Config.MetricInterval != tc.wantInterval {
				t.Errorf("Expected %v defaults when GENKIT_ENV=%s, got %v", tc.wantInterval, tc.env, defaults.Config.MetricInterval)
			}
			if defaults.Config.Export != tc.wantExport {
				t.Errorf("Expected export=%v for %s defaults", tc.wantExport, tc.env)
			}
		})
	}
}

func TestEnvDetection(t *testing.T) {
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

	// Clean up
	os.Unsetenv("GENKIT_ENV")
}

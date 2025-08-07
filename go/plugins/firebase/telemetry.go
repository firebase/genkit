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

package firebase

import (
	"log/slog"
	"os"

	"github.com/firebase/genkit/go/plugins/googlecloud"
)

// FirebaseTelemetryOptions provides configuration for Firebase telemetry.
// Uses a simple, opinionated approach focused on ease of use and comprehensive observability.
//
// Environment Variables:
// - GENKIT_ENV: Set to "dev" to disable export unless ForceExport is true
// - FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT: Auto-detected project ID if ProjectID is not set
type FirebaseTelemetryOptions struct {
	// ProjectID is the Firebase/Google Cloud project ID.
	// If empty, will be read from FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT environment variables.
	ProjectID string

	// ForceExport forces telemetry export even in development environment.
	// Defaults to false (only exports in production unless forced).
	ForceExport bool

	// ExportInputAndOutput includes AI model input/output in telemetry traces.
	// Defaults to false for privacy (only metadata is exported).
	ExportInputAndOutput bool
}

// FirebaseTelemetry creates a Google Cloud telemetry plugin configured for Firebase.
// This enables comprehensive telemetry export to Genkit Monitoring, backed by the Google Cloud
// Observability suite (Cloud Logging, Metrics, and Trace).
//
// This function uses opinionated defaults designed for Firebase applications:
// - All telemetry modules are automatically enabled for comprehensive observability
// - Environment-aware performance settings optimize for development vs production
// - Simple configuration focused on the most commonly needed options
// - Automatic project ID detection from Firebase/Google Cloud environment variables
//
// For more granular control over individual telemetry modules, use the googlecloud plugin directly.
//
// Example usage:
//
//	// Zero-config (auto-detects everything, all modules enabled)
//	g, err := genkit.Init(ctx, genkit.WithPlugins(firebase.FirebaseTelemetry()))
//
//	// With configuration (all modules still enabled)
//	g, err := genkit.Init(ctx, genkit.WithPlugins(firebase.FirebaseTelemetry(&firebase.FirebaseTelemetryOptions{
//		ProjectID:            "my-firebase-project",
//		ForceExport:          true,
//		ExportInputAndOutput: true,
//	})))
func FirebaseTelemetry(options ...*FirebaseTelemetryOptions) *googlecloud.GoogleCloud {
	var opts *FirebaseTelemetryOptions
	if len(options) > 0 && options[0] != nil {
		opts = options[0]
	}
	return buildTelemetryPlugin(opts)
}

// buildTelemetryPlugin is the internal function that actually creates the plugin.
func buildTelemetryPlugin(options *FirebaseTelemetryOptions) *googlecloud.GoogleCloud {
	slog.Debug("Initializing Firebase Genkit Monitoring.")

	// Use default options if none provided
	if options == nil {
		options = &FirebaseTelemetryOptions{}
	}

	// Resolve project ID from options or environment
	projectID := resolveFirebaseProjectID(options.ProjectID)
	if projectID == "" {
		slog.Warn("Firebase project ID not found. Set FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT environment variable, or pass ProjectID in options.")
	}

	// Convert Firebase options to Google Cloud options
	// Firebase provides opinionated defaults with all telemetry modules enabled for comprehensive observability
	gcOptions := &googlecloud.GoogleCloudTelemetryOptions{
		ProjectID:            projectID,
		ForceExport:          options.ForceExport,
		ExportInputAndOutput: options.ExportInputAndOutput,
	}

	// Use the simplified Google Cloud telemetry API
	return googlecloud.EnableGoogleCloudTelemetry(gcOptions)
}

// resolveFirebaseProjectID resolves the Firebase project ID from various sources.
// Priority: 1) Provided projectID, 2) FIREBASE_PROJECT_ID, 3) GOOGLE_CLOUD_PROJECT
func resolveFirebaseProjectID(projectID string) string {
	if projectID != "" {
		return projectID
	}

	// Try Firebase-specific environment variable first
	if envID := os.Getenv("FIREBASE_PROJECT_ID"); envID != "" {
		return envID
	}

	// Fall back to Google Cloud project ID
	return os.Getenv("GOOGLE_CLOUD_PROJECT")
}

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

	"golang.org/x/oauth2/google"
)

// GcpPrincipal represents the current GCP principal information
type GcpPrincipal struct {
	ProjectID           string `json:"project_id,omitempty"`
	ServiceAccountEmail string `json:"service_account_email,omitempty"`
}

// GcpAuthConfig represents authentication configuration for GCP
type GcpAuthConfig struct {
	ProjectID   string
	Credentials *google.Credentials
}

// CredentialsFromEnvironment allows Google Cloud credentials to be passed in "raw" as an environment
// variable. This is helpful in environments where the developer has limited
// ability to configure their compute environment, but does have the ability to
// set environment variables.
//
// This is different from the GOOGLE_APPLICATION_CREDENTIALS used by ADC, which
// represents a path to a credential file on disk. In *most* cases, even for
// 3rd party cloud providers, developers *should* attempt to use ADC, which
// searches for credential files in standard locations, before using this
// method.
//
// See also: https://cloud.google.com/docs/authentication/provide-credentials-adc
func CredentialsFromEnvironment() (*GcpAuthConfig, error) {
	ctx := context.Background()
	config := &GcpAuthConfig{}

	// Check for GCLOUD_SERVICE_ACCOUNT_CREDS environment variable
	if credsJSON := os.Getenv("GCLOUD_SERVICE_ACCOUNT_CREDS"); credsJSON != "" {
		slog.Debug("Retrieving credentials from GCLOUD_SERVICE_ACCOUNT_CREDS")

		// Parse the service account credentials
		var serviceAccountCreds map[string]interface{}
		if err := json.Unmarshal([]byte(credsJSON), &serviceAccountCreds); err != nil {
			return nil, fmt.Errorf("failed to parse GCLOUD_SERVICE_ACCOUNT_CREDS: %w", err)
		}

		// Create credentials from service account JSON
		creds, err := google.CredentialsFromJSON(ctx, []byte(credsJSON))
		if err != nil {
			return nil, fmt.Errorf("failed to create credentials from service account: %w", err)
		}

		config.Credentials = creds

		// Extract project ID from service account JSON
		if projectID, ok := serviceAccountCreds["project_id"].(string); ok && projectID != "" {
			config.ProjectID = projectID
		}
	} else {
		// Fall back to Application Default Credentials (ADC)
		slog.Debug("Using Application Default Credentials (ADC)")

		creds, err := google.FindDefaultCredentials(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to find default credentials: %w", err)
		}

		config.Credentials = creds
		config.ProjectID = creds.ProjectID
	}

	// If we still don't have a project ID, try to get it from the credentials
	if config.ProjectID == "" && config.Credentials != nil {
		if config.Credentials.ProjectID != "" {
			config.ProjectID = config.Credentials.ProjectID
		}
	}

	return config, nil
}

// ResolveCurrentPrincipal resolves the currently configured principal, either from the Genkit specific
// GCLOUD_SERVICE_ACCOUNT_CREDS environment variable, or from ADC.
//
// Since the Google Cloud Telemetry Exporter will discover credentials on its
// own, we don't immediately have access to the current principal. This method
// can be handy to get access to the current credential for logging debugging
// information or other purposes.
func ResolveCurrentPrincipal() (*GcpPrincipal, error) {
	ctx := context.Background()
	principal := &GcpPrincipal{}

	// Try environment credentials first
	envConfig, err := CredentialsFromEnvironment()
	if err != nil {
		slog.Debug("Could not retrieve credentials from environment", "error", err)

		// Try ADC fallback
		adcCreds, adcErr := google.FindDefaultCredentials(ctx)
		if adcErr != nil {
			slog.Debug("Could not retrieve credentials from ADC", "error", adcErr)
			return principal, fmt.Errorf("could not resolve credentials from environment or ADC: %w", err)
		}

		principal.ProjectID = adcCreds.ProjectID
		if email := extractServiceAccountEmail(adcCreds); email != "" {
			principal.ServiceAccountEmail = email
		}

		return principal, nil
	}

	// Use environment credentials
	principal.ProjectID = envConfig.ProjectID
	if email := extractServiceAccountEmail(envConfig.Credentials); email != "" {
		principal.ServiceAccountEmail = email
	}

	return principal, nil
}

// extractServiceAccountEmail extracts the service account email from Google credentials
func extractServiceAccountEmail(creds *google.Credentials) string {
	if creds == nil {
		return ""
	}

	// Try to extract from JWT token if available
	if creds.JSON != nil {
		var serviceAccount map[string]interface{}
		if err := json.Unmarshal(creds.JSON, &serviceAccount); err == nil {
			if email, ok := serviceAccount["client_email"].(string); ok {
				return email
			}
		}
	}

	// If we can't extract from JSON, try to get from token source
	// This is a fallback for cases where we have credentials but no JSON
	// Note: This is a simplified implementation - in practice, extracting
	// the service account email from a token source requires more complex logic
	return ""
}

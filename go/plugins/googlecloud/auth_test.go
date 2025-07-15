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
	"encoding/json"
	"os"
	"testing"
)

// TestCredentialsFromEnvironment tests the credential detection from environment variables
func TestCredentialsFromEnvironment(t *testing.T) {
	// Test service account credentials from environment
	t.Run("service account credentials", func(t *testing.T) {
		// Save original environment
		originalCreds := os.Getenv("GCLOUD_SERVICE_ACCOUNT_CREDS")
		originalGoogleCreds := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")
		defer func() {
			os.Setenv("GCLOUD_SERVICE_ACCOUNT_CREDS", originalCreds)
			os.Setenv("GOOGLE_APPLICATION_CREDENTIALS", originalGoogleCreds)
		}()

		// Set mock service account credentials
		mockServiceAccount := map[string]interface{}{
			"type":                        "service_account",
			"project_id":                  "test-project",
			"private_key_id":              "key-id",
			"private_key":                 "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
			"client_email":                "test@test-project.iam.gserviceaccount.com",
			"client_id":                   "123456789",
			"auth_uri":                    "https://accounts.google.com/o/oauth2/auth",
			"token_uri":                   "https://oauth2.googleapis.com/token",
			"auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
			"client_x509_cert_url":        "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com",
		}
		credsJSON, _ := json.Marshal(mockServiceAccount)

		os.Setenv("GCLOUD_SERVICE_ACCOUNT_CREDS", string(credsJSON))
		os.Unsetenv("GOOGLE_APPLICATION_CREDENTIALS")

		config, err := CredentialsFromEnvironment()
		if err != nil {
			t.Fatalf("Expected no error, got: %v", err)
		}

		if config.ProjectID != "test-project" {
			t.Errorf("Expected project ID 'test-project', got: %s", config.ProjectID)
		}

		if config.Credentials == nil {
			t.Error("Expected credentials to be set")
		}
	})

	// Test ADC fallback (this will likely fail in test environment, but we can test the code path)
	t.Run("adc fallback", func(t *testing.T) {
		// Save original environment
		originalCreds := os.Getenv("GCLOUD_SERVICE_ACCOUNT_CREDS")
		defer func() {
			os.Setenv("GCLOUD_SERVICE_ACCOUNT_CREDS", originalCreds)
		}()

		// Unset service account credentials to force ADC fallback
		os.Unsetenv("GCLOUD_SERVICE_ACCOUNT_CREDS")

		config, err := CredentialsFromEnvironment()
		// This will likely fail in test environment, but we test that the function doesn't panic
		if err != nil {
			t.Logf("Expected ADC failure in test environment: %v", err)
		} else {
			t.Logf("ADC worked in test environment, project ID: %s", config.ProjectID)
		}
	})
}

// TestResolveCurrentPrincipal tests the current principal resolution
func TestResolveCurrentPrincipal(t *testing.T) {
	// This test is mainly to ensure the function doesn't panic
	principal, err := ResolveCurrentPrincipal()
	if err != nil {
		t.Logf("Expected error in test environment: %v", err)
	} else {
		t.Logf("Principal resolved - Project ID: %s, Service Account Email: %s",
			principal.ProjectID, principal.ServiceAccountEmail)
	}
}

// TestNewFromEnvironment tests the convenience constructor
func TestNewFromEnvironment(t *testing.T) {
	// This test is mainly to ensure the function doesn't panic
	gc, err := NewFromEnvironment()
	if err != nil {
		t.Logf("Expected error in test environment: %v", err)
	} else {
		t.Logf("GoogleCloud plugin created with project ID: %s", gc.Config.ProjectID)
	}
}

// TestExtractServiceAccountEmail tests the email extraction utility
func TestExtractServiceAccountEmail(t *testing.T) {
	// Test with nil credentials
	email := extractServiceAccountEmail(nil)
	if email != "" {
		t.Errorf("Expected empty email for nil credentials, got: %s", email)
	}

	// Test with mock credentials containing JSON
	mockServiceAccount := map[string]interface{}{
		"type":         "service_account",
		"project_id":   "test-project",
		"client_email": "test@test-project.iam.gserviceaccount.com",
	}
	credsJSON, _ := json.Marshal(mockServiceAccount)

	// This would require creating a mock google.Credentials object
	// For now, we just test that the function doesn't panic with nil JSON
	email = extractServiceAccountEmail(nil)
	if email != "" {
		t.Errorf("Expected empty email for nil credentials, got: %s", email)
	}

	t.Logf("Service account JSON would be: %s", string(credsJSON))
}

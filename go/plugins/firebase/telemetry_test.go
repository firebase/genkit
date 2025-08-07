package firebase

import (
	"os"
	"testing"
)

func TestEnableFirebaseTelemetry(t *testing.T) {
	// Test zero config doesn't crash
	plugin := FirebaseTelemetry()
	if plugin == nil || plugin.Name() != "googlecloud" {
		t.Error("Expected valid googlecloud plugin")
	}

	// Test with options doesn't crash
	options := &FirebaseTelemetryOptions{
		ProjectID:   "test-project",
		ForceExport: true,
	}
	plugin = FirebaseTelemetry(options)
	if plugin == nil || plugin.Name() != "googlecloud" {
		t.Error("Expected valid googlecloud plugin with options")
	}
}

func TestProjectIDResolution(t *testing.T) {
	tests := []struct {
		input    string
		fbEnv    string
		gcpEnv   string
		expected string
	}{
		{"explicit", "firebase", "gcp", "explicit"}, // Explicit wins
		{"", "firebase", "gcp", "firebase"},         // Firebase env wins
		{"", "", "gcp", "gcp"},                      // GCP fallback
		{"", "", "", ""},                            // Empty fallback
	}

	for _, tt := range tests {
		if tt.fbEnv != "" {
			os.Setenv("FIREBASE_PROJECT_ID", tt.fbEnv)
		} else {
			os.Unsetenv("FIREBASE_PROJECT_ID")
		}
		if tt.gcpEnv != "" {
			os.Setenv("GOOGLE_CLOUD_PROJECT", tt.gcpEnv)
		} else {
			os.Unsetenv("GOOGLE_CLOUD_PROJECT")
		}

		result := resolveFirebaseProjectID(tt.input)
		if result != tt.expected {
			t.Errorf("resolveFirebaseProjectID(%q) = %q, want %q", tt.input, result, tt.expected)
		}

		// Cleanup
		os.Unsetenv("FIREBASE_PROJECT_ID")
		os.Unsetenv("GOOGLE_CLOUD_PROJECT")
	}
}

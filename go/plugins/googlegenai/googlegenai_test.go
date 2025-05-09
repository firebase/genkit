// googlegenai_test.go
package googlegenai

import (
	"context"
	"fmt"
	"os"
	"strings"
	"testing"

	"google.golang.org/genai"
)

func TestAPIErrors(t *testing.T) {
	ctx := context.Background()
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		t.Skip("GEMINI_API_KEY environment variable not set")
	}

	// 1. Test error handing with real API calls
	t.Run("ErrorHandlingWithRealCalls", func(t *testing.T) {
		// Create client with valid API key
		gc := genai.ClientConfig{
			Backend: genai.BackendGeminiAPI,
			APIKey:  apiKey,
		}

		client, err := genai.NewClient(ctx, &gc)
		if err != nil {
			t.Fatalf("Failed to create client: %v", err)
		}

		// Test with invalid model name (should produce error)
		_, err = client.Models.GenerateContent(ctx, "non-existent-model", nil, nil)
		if err == nil {
			t.Fatal("Expected error with invalid model, got none")
		}

		// Test our error formatting
		formattedErr := extractAndFormatAPIError(err)

		// Check that the error is properly formatted
		t.Logf("Original error: %v", err)
		t.Logf("Formatted error: %v", formattedErr)

		// Verify the error contains useful information
		if !strings.Contains(formattedErr.Error(), "error from Google AI service") &&
			!strings.Contains(formattedErr.Error(), "400") &&
			!strings.Contains(formattedErr.Error(), "404") {
			t.Errorf("Formatted error doesn't contain expected information: %v", formattedErr)
		}
	})

	// 2. Test 401 (Unauthorized) - Invalid API Key
	t.Run("Unauthorized401", func(t *testing.T) {
		// For this test, we'll just simulate a 401 error instead of making an actual API call
		simulatedError := fmt.Errorf("error: status code 401: Unauthorized")

		formattedErr := extractAndFormatAPIError(simulatedError)

		if !strings.Contains(formattedErr.Error(), "unauthorized (HTTP 401)") {
			t.Fatalf("Expected 401 error formatting but got: %v", formattedErr)
		}

		t.Logf("Successfully formatted 401 error: %v", formattedErr)
	})

	// 3. Test 403 (Forbidden) - Access to restricted model
	t.Run("Forbidden403", func(t *testing.T) {
		gc := genai.ClientConfig{
			Backend: genai.BackendGeminiAPI,
			APIKey:  apiKey,
		}

		client, err := genai.NewClient(ctx, &gc)
		if err != nil {
			t.Fatalf("Failed to create client: %v", err)
		}

		// Try to access a potentially restricted model
		_, err = client.Chats.Create(ctx, "restricted-model-name", nil, nil)
		if err == nil {
			t.Skip("No 403 error - either model exists or permissions are sufficient")
		}

		formattedErr := extractAndFormatAPIError(err)
		if strings.Contains(err.Error(), "403") {
			t.Logf("Successfully triggered 403: %v", formattedErr)
		} else {
			t.Logf("Got error but not 403: %v", formattedErr)
		}
	})

	// 4. For the 400 (Bad Request) test
	t.Run("BadRequest400", func(t *testing.T) {
		gc := genai.ClientConfig{
			Backend: genai.BackendGeminiAPI,
			APIKey:  apiKey,
		}

		client, err := genai.NewClient(ctx, &gc)
		if err != nil {
			t.Fatalf("Failed to create client: %v", err)
		}

		// Try more obviously invalid parameters
		// 1. Try an empty model name
		t.Logf("Testing with empty model name...")
		_, err = client.Chats.Create(ctx, "", nil, nil)
		if err != nil {
			formattedErr := extractAndFormatAPIError(err)
			t.Logf("Error with empty model: %v", formattedErr)
		}

		// 2. Try with extremely long invalid model name
		t.Logf("Testing with extremely long model name...")
		longModelName := strings.Repeat("invalid-model", 50)
		_, err = client.Chats.Create(ctx, longModelName, nil, nil)
		if err != nil {
			formattedErr := extractAndFormatAPIError(err)
			t.Logf("Error with long model name: %v", formattedErr)
		}

		// 3. Try with special characters
		t.Logf("Testing with special characters in model name...")
		_, err = client.Chats.Create(ctx, "$$$$^^^%%%", nil, nil)
		if err != nil {
			formattedErr := extractAndFormatAPIError(err)
			t.Logf("Error with special chars: %v", formattedErr)
		}

		if err == nil {
			t.Skip("Could not trigger a 400 error with any of the invalid inputs")
		}
	})

	// 5. Test 429 (Rate Limit) - Too many requests
	t.Run("RateLimit429", func(t *testing.T) {
		gc := genai.ClientConfig{
			Backend: genai.BackendGeminiAPI,
			APIKey:  apiKey,
		}

		client, err := genai.NewClient(ctx, &gc)
		if err != nil {
			t.Fatalf("Failed to create client: %v", err)
		}

		// Try to trigger rate limit with multiple rapid requests
		for i := 0; i < 10; i++ {
			_, err = client.Chats.Create(ctx, "gemini-2.0-flash", nil, nil)
			if err != nil {
				formattedErr := extractAndFormatAPIError(err)
				if strings.Contains(err.Error(), "429") {
					t.Logf("Successfully triggered 429: %v", formattedErr)
					return
				}
			}
		}

		t.Skip("Could not trigger 429 rate limit error with 10 requests")
	})
}

// Add this to test your error extraction function
func TestExtractAndFormatAPIError(t *testing.T) {
	testCases := []struct {
		name     string
		err      error
		expected string
	}{
		{
			name:     "401 Error",
			err:      fmt.Errorf("error: status code 401: Unauthorized"),
			expected: "unauthorized (HTTP 401)",
		},
		{
			name:     "403 Error",
			err:      fmt.Errorf("error: status code 403: Forbidden"),
			expected: "forbidden (HTTP 403)",
		},
		{
			name:     "429 Error",
			err:      fmt.Errorf("error: status code 429: Too Many Requests"),
			expected: "rate limit exceeded (HTTP 429)",
		},
		{
			name:     "400 Error",
			err:      fmt.Errorf("error: status code 400: Bad Request"),
			expected: "bad request (HTTP 400)",
		},
		{
			name:     "500 Error",
			err:      fmt.Errorf("error: status code 500: Internal Server Error"),
			expected: "server error (HTTP 500)",
		},
		{
			name:     "Unknown Error",
			err:      fmt.Errorf("some random error"),
			expected: "error from Google AI service",
		},
		{
			name:     "Nil Error",
			err:      nil,
			expected: "",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			formatted := extractAndFormatAPIError(tc.err)

			// Handle nil case specially
			if tc.err == nil {
				if formatted != nil {
					t.Errorf("Expected nil error for nil input, got: %v", formatted)
				}
				return
			}

			if !strings.Contains(formatted.Error(), tc.expected) {
				t.Errorf("Expected error to contain '%s', got: %v", tc.expected, formatted)
			}
		})
	}
}

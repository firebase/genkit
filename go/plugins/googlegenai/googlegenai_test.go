// googlegenai_test.go
package googlegenai

import (
	"context"
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"google.golang.org/genai"
)

func TestAPIErrors(t *testing.T) {
	ctx := context.Background()
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		t.Skip("GEMINI_API_KEY environment variable not set")
	}

	// 1. Test valid API key
	t.Run("ValidAPIKey", func(t *testing.T) {
		invalidAPIKeys := []string{
			"invalid-key-123",
			"",
			"AI" + strings.Repeat("x", 30),
		}

		for _, invalidAPIKey := range invalidAPIKeys {
			t.Logf("Testing invalid key: %s", invalidAPIKey)

			gc := genai.ClientConfig{
				Backend: genai.BackendGeminiAPI,
				APIKey:  invalidAPIKey,
			}

			client, err := genai.NewClient(ctx, &gc)
			t.Logf("Client creation result: %v", err)

			if err != nil {
				continue // Skip to next key if we can't even create a client
			}

			// Try to make an API call
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()

			_, err = client.Chats.Create(ctx, "gemini-2.0-flash", nil, nil)
			t.Logf("API call result: %v", err)

			if err == nil {
				t.Logf("Unexpected: No error returned with invalid key!")
				continue

			}

			t.Logf("Error type: %T", err)
			t.Logf("Error contains '401': %v", strings.Contains(err.Error(), "401"))
			t.Logf("Error contains 'unauthorized': %v", strings.Contains(strings.ToLower(err.Error()), "unauthorized"))
			t.Logf("Error contains 'invalid': %v", strings.Contains(strings.ToLower(err.Error()), "invalid"))
		}
	})

	// 2. Test 401 (Unauthorized) - Invalid API Key
	t.Run("Unauthorized401", func(t *testing.T) {
		gc := genai.ClientConfig{
			Backend: genai.BackendGeminiAPI,
			APIKey:  "invalid-key-deliberately-wrong",
		}

		badClient, err := genai.NewClient(ctx, &gc)
		if err != nil {
			t.Logf("Failed at client creation: %v", err)
			if strings.Contains(err.Error(), "401") {
				return // Test passed - caught at client creation
			}
		}

		// If client creation succeeded, try to use it
		_, err = badClient.Chats.Create(ctx, "gemini-2.0-flash", nil, nil)
		if err == nil {
			t.Fatal("Expected 401 error but got none")
		}

		if !strings.Contains(err.Error(), "401") {
			t.Fatalf("Expected 401 error but got: %v", err)
		}
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

		if strings.Contains(err.Error(), "403") {
			t.Logf("Successfully triggered 403: %v", err)
		} else {
			t.Logf("Got error but not 403: %v", err)
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
			t.Logf("Error with empty model: %v", err)
		}

		// 2. Try with extremely long invalid model name
		t.Logf("Testing with extremely long model name...")
		longModelName := strings.Repeat("invalid-model", 50)
		_, err = client.Chats.Create(ctx, longModelName, nil, nil)
		if err != nil {
			t.Logf("Error with long model name: %v", err)
		}

		// 3. Try with special characters
		t.Logf("Testing with special characters in model name...")
		_, err = client.Chats.Create(ctx, "$$$$^^^%%%", nil, nil)
		if err != nil {
			t.Logf("Error with special chars: %v", err)
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
			if err != nil && strings.Contains(err.Error(), "429") {
				t.Logf("Successfully triggered 429: %v", err)
				return
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
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			formatted := extractAndFormatAPIError(tc.err)
			if !strings.Contains(formatted.Error(), tc.expected) {
				t.Errorf("Expected error to contain '%s', got: %v", tc.expected, formatted)
			}
		})
	}
}

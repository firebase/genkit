package client_test

import (
	"context"
	"flag"
	"os"
	"testing"

	"github.com/firebase/genkit/go/plugins/openai/client"
)

var apiKey = flag.String("api-key", "", "OpenAI API key")
var testLive = flag.Bool("test-live", false, "run live tests")

func TestLiveChat(t *testing.T) {
	if !*testLive {
		t.Skip("skipping live OpenAI API test. Use -test-live flag to run")
	}

	// Get API key from flag or environment variable
	key := *apiKey
	if key == "" {
		key = os.Getenv("OPENAI_API_KEY")
	}

	if key == "" {
		t.Skip("skipping live test: no API key provided. Use -api-key flag or set OPENAI_API_KEY environment variable")
	}

	// Create a new client
	c, err := client.NewClient(key).Build()
	if err != nil {
		t.Fatalf("failed to create client: %v", err)
	}

	// Build and execute a simple chat request
	resp, err := c.NewChat("gpt-3.5-turbo").
		AddMessage(client.RoleUser, "Say hello in a creative way").
		WithTemperature(0.7).
		Execute(context.Background())

	if err != nil {
		t.Fatalf("failed to execute chat: %v", err)
	}

	if len(resp.Choices) == 0 {
		t.Fatal("expected at least one response choice")
	}

	content := resp.Choices[0].Message.Content
	if content == "" {
		t.Fatal("expected non-empty response content")
	}

	t.Logf("Response: %s", content)
}

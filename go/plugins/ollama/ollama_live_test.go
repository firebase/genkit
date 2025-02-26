// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ollama_test

import (
	"context"
	"flag"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	ollamaPlugin "github.com/firebase/genkit/go/plugins/ollama"
)

var serverAddress = flag.String("server-address", "http://localhost:11434", "Ollama server address")
var modelName = flag.String("model-name", "tinyllama", "model name")
var testLive = flag.Bool("test-live", false, "run live tests")

/*
To run this test, you need to have the Ollama server running. You can set the server address using the OLLAMA_SERVER_ADDRESS environment variable.
If the environment variable is not set, the test will default to http://localhost:11434 (the default address for the Ollama server).
*/
func TestLive(t *testing.T) {

	if !*testLive {
		t.Skip("skipping go/plugins/ollama live test")
	}

	ctx := context.Background()

	g, err := genkit.Init(context.Background())
	if err != nil {
		t.Fatal(err)
	}

	// Initialize the Ollama plugin
	err = ollamaPlugin.Init(ctx, &ollamaPlugin.Config{
		ServerAddress: *serverAddress,
	})
	if err != nil {
		t.Fatalf("failed to initialize Ollama plugin: %s", err)
	}

	// Define the model
	ollamaPlugin.DefineModel(g, ollamaPlugin.ModelDefinition{Name: *modelName}, nil)

	// Use the Ollama model
	m := ollamaPlugin.Model(g, *modelName)
	if m == nil {
		t.Fatalf(`failed to find model: %s`, *modelName)
	}

	// Generate a response from the model
	resp, err := genkit.GenerateWithRequest(ctx, g, m,
		ai.NewModelRequest(
			&ai.GenerationCommonConfig{Temperature: 1},
			ai.NewUserTextMessage("I'm hungry, what should I eat?")),
		nil, nil, nil)
	if err != nil {
		t.Fatalf("failed to generate response: %s", err)
	}

	if resp == nil {
		t.Fatalf("response is nil")
	}

	// Get the text from the response
	text := resp.Text()
	// log.Println("Response:", text)

	// Assert that the response text is as expected
	if text == "" {
		t.Fatalf("expected non-empty response, got: %s", text)
	}
}

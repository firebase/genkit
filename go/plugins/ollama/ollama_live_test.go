// Copyright 2024 Google LLC
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

package ollama

import (
	"context"
	"flag"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

var serverAddress = flag.String("server-address", "http://localhost:11434", "Ollama server address")
var modelName = flag.String("model-name", "tinyllama", "model name")
var testLive = flag.Bool("test-live", false, "run live tests")

/*
To run this test, you need to have the Ollama server running. You can set the server address using the OLLAMA_SERVER_ADDRESS environment variable.
If the environment variable is not set, the test will default to http://localhost:11434 (the default address for the Ollama server).

Note sometimes this test will fail because the model isn't responding in the correct format.
*/
func TestLive(t *testing.T) {
	if !*testLive {
		t.Skip("skipping go/plugins/ollama live test")
	}

	ctx := context.Background()

	// Initialize the Ollama plugin
	err := Init(ctx, &Config{
		ServerAddress: *serverAddress,
	})
	defer uninit()

	if err != nil {
		t.Fatalf("failed to initialize Ollama plugin: %s", err)
	}

	// Define the model
	DefineModel(ModelDefinition{Name: *modelName}, nil)

	// Use the Ollama model
	m := Model(*modelName)
	if m == nil {
		t.Fatalf("failed to find model: %s", *modelName)
	}

	// type GenerateRequestOutput struct {
	// 	Format OutputFormat   `json:"format,omitempty"`
	// 	Schema map[string]any `json:"schema,omitempty"`
	// }

	// schema should be {suggestion: string}

	request, err := ai.NewGenerateRequestWithOutput(
		&ai.GenerationCommonConfig{Temperature: 1},
		&ai.GenerateRequestOutput{
			Format: ai.OutputFormatJSON,
			Schema: map[string]interface{}{
				"suggestion": "string",
			},
		},
		ai.NewUserTextMessage("I'm hungry, what should I eat?"),
	)

	if err != nil {
		t.Fatalf("failed to create generate request: %s", err)
	}

	// Generate a response from the model
	resp, err := m.Generate(ctx, request, nil)
	if err != nil {
		t.Fatalf("failed to generate response: %s", err)
	}

	if resp == nil {
		t.Fatalf("response is nil")
	}

	// Get the text from the response
	text := resp.Text()

	// Assert that the response text is as expected
	if text == "" {
		t.Fatalf("expected non-empty response, got: %s", text)
	}
}

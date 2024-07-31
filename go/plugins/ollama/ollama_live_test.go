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

package ollama_test

import (
	"context"
	"fmt"
	"log"
	"testing"

	"github.com/docker/docker/client"
	"github.com/docker/go-connections/nat"
	"github.com/firebase/genkit/go/ai"
	ollamaPlugin "github.com/firebase/genkit/go/plugins/ollama"
	ollamaTestContainers "github.com/testcontainers/testcontainers-go/modules/ollama"
)

// setupOllamaContainer sets up the Ollama container and returns the server address.
func setupOllamaContainer(ctx context.Context) (string, func(), error) {
	// Start the Ollama container
	ollamaContainer, err := ollamaTestContainers.Run(ctx, "ollama/ollama:0.1.26")
	if err != nil {
		return "", nil, fmt.Errorf("failed to start container: %w", err)
	}

	cleanup := func() {
		if err := ollamaContainer.Terminate(ctx); err != nil {
			log.Printf("failed to terminate container: %s", err)
		}
	}

	// Get the container information
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		cleanup()
		return "", nil, fmt.Errorf("failed to create docker client: %w", err)
	}
	containerID := ollamaContainer.GetContainerID()
	containerInfo, err := cli.ContainerInspect(ctx, containerID)
	if err != nil {
		cleanup()
		return "", nil, fmt.Errorf("failed to inspect container: %w", err)
	}

	// Retrieve the host port for the container's port 11434
	portBindings := containerInfo.NetworkSettings.Ports[nat.Port("11434/tcp")]
	if len(portBindings) == 0 {
		cleanup()
		return "", nil, fmt.Errorf("no port bindings found for port 11434/tcp")
	}
	hostPort := portBindings[0].HostPort

	// Pull the model
	_, _, err = ollamaContainer.Exec(ctx, []string{"ollama", "pull", "tinyllama"})
	if err != nil {
		cleanup()
		return "", nil, fmt.Errorf("failed to pull model: %w", err)
	}

	// Return the server address and cleanup function
	serverAddress := fmt.Sprintf("http://localhost:%s", hostPort)
	return serverAddress, cleanup, nil
}

func TestWithOllamaContainer(t *testing.T) {
	ctx := context.Background()

	// Setup the Ollama container
	serverAddress, cleanup, err := setupOllamaContainer(ctx)
	if err != nil {
		t.Fatalf("setupOllamaContainer failed: %s", err)
	}
	defer cleanup()

	// Initialize the Ollama plugin
	err = ollamaPlugin.Init(ctx, &ollamaPlugin.Config{
		ServerAddress: serverAddress,
	})
	if err != nil {
		t.Fatalf("failed to initialize Ollama plugin: %s", err)
	}

	// Define the model
	ollamaPlugin.DefineModel(ollamaPlugin.ModelDefinition{Name: "tinyllama"}, nil)

	// Use the Ollama model
	m := ollamaPlugin.Model("tinyllama")
	if m == nil {
		t.Fatalf("failed to find model: tinyllama")
	}

	// Generate a response from the model
	resp, err := m.Generate(ctx,
		ai.NewGenerateRequest(
			&ai.GenerationCommonConfig{Temperature: 1},
			ai.NewUserTextMessage("I'm hungry, what should I eat?")),
		nil)
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

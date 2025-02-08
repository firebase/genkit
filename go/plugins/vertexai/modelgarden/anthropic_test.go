// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden_test

import (
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/vertexai/modelgarden"
)

// keep track of all clients
var clients = modelgarden.NewClientFactory()

func TestAnthropicClient(t *testing.T) {
	anthropicClient, err := clients.CreateClient(&modelgarden.ClientConfig{
		Region:   "us-west-1",
		Provider: "anthropic",
		Project:  "project-123",
	})
	if err != nil {
		t.Fatalf("unable to create anthropic client")
	}

	err = anthropicClient.DefineModel("foo_model", &ai.ModelInfo{})
	if err != nil {
		t.Fatalf("unable to define model: %v", err)
	}
}

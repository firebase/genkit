// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"errors"
	"fmt"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// Generic Client interface for supported provider clients
type Client interface {
	DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error)
}

type ClientFactory struct {
	creators map[string]ClientCreator // cache for client creation functions
	clients  map[string]Client        // cache for provider clients
	mu       sync.Mutex
}

func NewClientFactory() *ClientFactory {
	return &ClientFactory{
		creators: make(map[string]ClientCreator),
		clients:  make(map[string]Client),
	}
}

// Basic client configuration
type ClientConfig struct {
	Provider string
	Project  string
	Region   string
}

type ClientCreator func(config any) (Client, error)

func (f *ClientFactory) Register(provider string, creator ClientCreator) {
	f.creators[provider] = creator
}

func (f *ClientFactory) CreateClient(config *ClientConfig) (Client, error) {
	if config == nil {
		return nil, errors.New("empty client config")
	}

	f.mu.Lock()
	defer f.mu.Unlock()

	// every client will be identified by its provider-region combination
	key := fmt.Sprintf("%s-%s", config.Provider, config.Region)
	if client, ok := f.clients[key]; ok {
		return client, nil // return from cache
	}

	creator, ok := f.creators[config.Provider]
	if !ok {
		return nil, fmt.Errorf("unknown client type: %s", key)
	}

	var client Client
	var err error
	switch config.Provider {
	case "anthropic":
		client, err = creator(&AnthropicClientConfig{
			Region:  config.Region,
			Project: config.Project,
		})
	}
	if err != nil {
		return nil, err
	}

	f.clients[key] = client

	return client, nil
}

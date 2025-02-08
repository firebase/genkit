// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"errors"
	"fmt"
	"sync"

	"github.com/firebase/genkit/go/ai"
)

// Generic Client interface for supported provider clients
type Client interface {
	DefineModel(name string, info *ai.ModelInfo) error
}

type ClientFactory struct {
	clients map[string]Client // cache for provider clients
	mu      sync.Mutex
}

func NewClientFactory() *ClientFactory {
	return &ClientFactory{
		clients: make(map[string]Client),
	}
}

const (
	Anthropic string = "anthropic"
)

// Function type for creating clients from supported providers
type ClientCreator func(region string, project string) (Client, error)

// Basic client configuration
type ClientConfig struct {
	Creator  ClientCreator
	Provider string
	Project  string
	Region   string
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

	var client Client
	var err error

	switch config.Provider {
	case Anthropic:
		client, err = AnthropicClient(config.Region, config.Project)
		if err != nil {
			return nil, err
		}
	}

	f.clients[key] = client

	return client, nil
}

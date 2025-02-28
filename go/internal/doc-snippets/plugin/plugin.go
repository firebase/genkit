// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package plugin

import (
	"fmt"
	"os"
)

// [START init]
type Config struct {
	ExampleAPIKey string
}

func Init(cfg *Config) (err error) {
	apiKey := cfg.ExampleAPIKey
	if apiKey == "" {
		apiKey = os.Getenv("EXAMPLE_API_KEY")
	}
	if apiKey == "" {
		return fmt.Errorf(`the Example plug-in requires you to specify an API
 key for the Example service, either by passing it to example.Init() or by
 setting the EXAMPLE_API_KEY environment variable`)
	}

	return nil
}

// [END init]

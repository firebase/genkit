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

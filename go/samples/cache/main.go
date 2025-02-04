// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func main() {
	projectID := os.Getenv("GCLOUD_PROJECT")
	if projectID == "" {
		fmt.Println("GCLOUD_PROJECT environment variable not set")
		return
	}
	location := os.Getenv("GCLOUD_LOCATION")
	if location == "" {
		fmt.Println("GCLOUD_LOCATION environment variable not set")
		return
	}
	var r, _ = registry.New()
	ctx := context.Background()
	g, err := genkit.New(&genkit.Options{
		DefaultModel: "vertexai/gemini-1.5-flash",
	})
	if err != nil {
		fmt.Println(err)
	}
	err = vertexai.Init(ctx, g, &vertexai.Config{ProjectID: projectID, Location: location})
	if err != nil {
		fmt.Println(err)
	}
	resp, err := ai.Generate(ctx, r,
		ai.WithConfig(&ai.GenerationCommonConfig{Temperature: 1, TTL: time.Hour}),
		ai.WithTextPrompt("Tell me a joke about golang developers"))

	if err != nil {
		fmt.Println(err)
	}
	fmt.Println("output:", resp.Message.Text())
}

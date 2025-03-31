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

package main

import (
	"context"
	"log"

	// Import Genkit and the Google AI plugin
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}), genkit.WithPromptDir("prompts"))
	if err != nil {
		log.Fatal(err)
	}

	// Look up the prompt by name
	prompt := genkit.LookupPrompt(g, "local", "greeting")
	if prompt == nil {
		log.Fatal("failed to find prompt")
	}

	input := map[string]interface{}{
		"name":     "World",
		"location": "Firebase",
	}

	// Execute the prompt with the provided input
	resp, err := prompt.Execute(ctx, ai.WithInput(input))
	if err != nil {
		log.Fatal(err)
	}
	text := resp.Text()
	log.Printf("Response: %s", text)
}

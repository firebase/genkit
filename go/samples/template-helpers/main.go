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
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

func main() {
	ctx := context.Background()

	g, err := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	if err != nil {
		log.Fatal(err)
	}
	
	genkit.DefineHelper(g, "upper", func(text string) string {
		return strings.ToUpper(text)
	})
	
	// Load prompts from the prompts directory
	err = genkit.LoadPromptDir(g, "prompts", "")
	if err != nil {
		log.Fatal("prompt not found")
	}
	
	// Get the prompt
	prompt := genkit.LookupPrompt(g, "", "greeting")
	if prompt == nil {
		log.Fatal("prompt not found")
	}
	
	// Prepare input data
	input := map[string]any{
		"name": 	"Alice",
		"location": 	"Firebase",
		"style":	"a pirate",
	}
	
	// Execute the prompt
	resp, err := prompt.Execute(ctx, ai.WithInput(input))
	if err != nil {
		log.Fatal(err)
	}
	text := resp.Text()
	log.Printf("Response: %s", text)
}


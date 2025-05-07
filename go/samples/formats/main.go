// Copyright 2025 Google LLC
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
	"net/http"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"github.com/firebase/genkit/go/plugins/server"
)

type StoryCharacter struct {
	Name       string `json:"name"`
	Age        int    `json:"age"`
	Hometown   string `json:"hometown"`
	Profession string `json:"profession"`
}

func main() {
	ctx := context.Background()
	g, err := genkit.Init(ctx,
		genkit.WithPlugins(&googlegenai.VertexAI{}),
		genkit.WithDefaultModel("vertexai/gemini-2.0-flash"),
	)
	if err != nil {
		log.Fatal(err)
	}

	defaultPrompt, err := genkit.DefinePrompt(g, "defaultInstructions",
		ai.WithPrompt("Generate a children's book story character about someone named {{name}}."),
		ai.WithOutputType([]StoryCharacter{}),
		ai.WithOutputFormat(ai.OutputFormatJSONL),
	)
	if err != nil {
		log.Fatal(err)
	}

	customPrompt, err := genkit.DefinePrompt(g, "customInstructions",
		ai.WithPrompt("Generate a children's book story character about someone named {{name}}."),
		ai.WithOutputInstructions("The output should be JSON and match the schema of the following object: "+
			"{name: string, age: number, homeTown: string, profession: string}"),
	)
	if err != nil {
		log.Fatal(err)
	}

	genkit.DefineFlow(g, "defaultInstructionsFlow", func(ctx context.Context, _ any) ([]*StoryCharacter, error) {
		resp, err := defaultPrompt.Execute(ctx, ai.WithInput(StoryCharacter{Name: "Willy the Pig"}))
		if err != nil {
			return nil, err
		}

		var defaultCharacter StoryCharacter
		if err := resp.Output(&defaultCharacter); err != nil {
			return nil, err
		}

		resp, err = customPrompt.Execute(ctx, ai.WithInput(StoryCharacter{Name: "Markie the Doberman"}))
		if err != nil {
			return nil, err
		}

		var customCharacter StoryCharacter
		if err := resp.Output(&customCharacter); err != nil {
			return nil, err
		}

		return []*StoryCharacter{&defaultCharacter, &customCharacter}, nil
	})

	mux := http.NewServeMux()
	for _, a := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+a.Name(), genkit.Handler(a))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}

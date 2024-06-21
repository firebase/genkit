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

// This program can be manually tested like so:
//
// In development mode (with the environment variable GENKIT_ENV="dev"):
// Start the server listening on port 3100:
//
//	go run . &
//
// Tell it to run a flow:
//
//	curl -d '{"key":"/flow/simpleQaFlow/simpleQaFlow", "input":{"start": {"input":{"question": "What is the capital of UK?"}}}}' http://localhost:3100/api/runAction
//
// In production mode (GENKIT_ENV missing or set to "prod"):
// Start the server listening on port 3400:
//
//	go run . &
//
// Tell it to run a flow:
//
//   curl -d '{"question": "What is the capital of UK?"}' http://localhost:3400/simpleQaFlow

package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/dotprompt"
	"github.com/firebase/genkit/go/plugins/googleai"
	"github.com/firebase/genkit/go/plugins/localvec"
	"github.com/invopop/jsonschema"
)

const simpleQaPromptTemplate = `
You're a helpful agent that answers the user's common questions based on the context provided.

Here is the user's query: {{query}}

Here is the context you should use: {{context}}

Please provide the best answer you can.
`

type simpleQaInput struct {
	Question string `json:"question"`
}

type simpleQaPromptInput struct {
	Query   string `json:"query"`
	Context string `json:"context"`
}

func main() {
	apiKey := os.Getenv("GOOGLE_GENAI_API_KEY")
	if apiKey == "" {
		fmt.Fprintln(os.Stderr, "rag example requires setting GOOGLE_GENAI_API_KEY in the environment.")
		fmt.Fprintln(os.Stderr, "You can get an API key at https://ai.google.dev.")
		os.Exit(1)
	}
	err := googleai.Init(context.Background(), googleai.Config{APIKey: apiKey})
	if err != nil {
		log.Fatal(err)
	}
	simpleQaPrompt, err := dotprompt.Define("simpleQaPrompt",
		simpleQaPromptTemplate,
		dotprompt.Config{
			ModelAction:  googleai.Model("gemini-1.0-pro"),
			InputSchema:  jsonschema.Reflect(simpleQaPromptInput{}),
			OutputFormat: ai.OutputFormatText,
		},
	)
	if err != nil {
		log.Fatal(err)
	}

	indexers, retrievers, err := localvec.Init(context.Background(), localvec.Config{
		Stores: []localvec.StoreConfig{
			{
				Name:     "simpleQa",
				Embedder: googleai.Embedder("embedding-001"),
			},
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	genkit.DefineFlow("simpleQaFlow", func(ctx context.Context, input *simpleQaInput) (string, error) {
		d1 := ai.DocumentFromText("Paris is the capital of France", nil)
		d2 := ai.DocumentFromText("USA is the largest importer of coffee", nil)
		d3 := ai.DocumentFromText("Water exists in 3 states - solid, liquid and gas", nil)

		indexerReq := &ai.IndexerRequest{
			Documents: []*ai.Document{d1, d2, d3},
		}
		err := ai.Index(ctx, indexers[0], indexerReq)
		if err != nil {
			return "", err
		}

		dRequest := ai.DocumentFromText(input.Question, nil)
		retrieverReq := &ai.RetrieverRequest{
			Document: dRequest,
		}
		response, err := ai.Retrieve(ctx, retrievers[0], retrieverReq)
		if err != nil {
			return "", err
		}

		var sb strings.Builder
		for _, d := range response.Documents {
			sb.WriteString(d.Content[0].Text)
			sb.WriteByte('\n')
		}

		promptInput := &simpleQaPromptInput{
			Query:   input.Question,
			Context: sb.String(),
		}

		resp, err := simpleQaPrompt.Generate(ctx,
			&dotprompt.PromptRequest{
				Variables: promptInput,
			},
			nil,
		)
		if err != nil {
			return "", err
		}
		text, err := resp.Text()
		if err != nil {
			return "", fmt.Errorf("simpleQa: %v", err)
		}
		return text, nil
	})

	if err := genkit.StartFlowServer(""); err != nil {
		log.Fatal(err)
	}
}

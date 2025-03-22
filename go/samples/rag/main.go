// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

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
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/evaluators"
	"github.com/firebase/genkit/go/plugins/googleai"
	"github.com/firebase/genkit/go/plugins/localvec"
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
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		log.Fatal(err)
	}
	err = googleai.Init(context.Background(), g, nil)
	if err != nil {
		log.Fatal(err)
	}
	model := googleai.Model(g, "gemini-2.0-flash")
	embedder := googleai.Embedder(g, "embedding-001")
	if embedder == nil {
		log.Fatal("embedder is not defined")
	}
	if err := localvec.Init(); err != nil {
		log.Fatal(err)
	}
	metrics := []evaluators.MetricConfig{
		{
			MetricType: evaluators.EvaluatorTypeDeepEqual,
		},
		{
			MetricType: evaluators.EvaluatorTypeRegex,
		},
		{
			MetricType: evaluators.EvaluatorTypeJsonata,
		},
	}
	evalConfig := evaluators.Config{Metrics: metrics}
	if err := evaluators.Init(ctx, g, &evalConfig); err != nil {
		log.Fatal(err)
	}
	indexer, retriever, err := localvec.DefineIndexerAndRetriever(g, "simpleQa", localvec.Config{Embedder: embedder})
	if err != nil {
		log.Fatal(err)
	}

	simpleQaPrompt, err := genkit.DefinePrompt(g, "simpleQaPrompt",
		ai.WithModel(model),
		ai.WithPromptText(simpleQaPromptTemplate),
		ai.WithInputType(simpleQaPromptInput{}),
		ai.WithOutputFormat(ai.OutputFormatText),
	)
	if err != nil {
		log.Fatal(err)
	}

	// Dummy evaluator for testing
	evalOptions := ai.EvaluatorOptions{
		DisplayName: "Simple Evaluator",
		Definition:  "Just says true or false randomly",
		IsBilled:    false,
	}
	genkit.DefineEvaluator(g, "custom", "simpleEvaluator", &evalOptions, func(ctx context.Context, req *ai.EvaluatorCallbackRequest) (*ai.EvaluatorCallbackResponse, error) {
		m := make(map[string]any)
		m["reasoning"] = "No good reason"
		score := ai.Score{
			Id:      "testScore",
			Score:   1,
			Status:  ai.ScoreStatusPass.String(),
			Details: m,
		}
		callbackResponse := ai.EvaluatorCallbackResponse{
			TestCaseId: req.Input.TestCaseId,
			Evaluation: []ai.Score{score},
		}
		return &callbackResponse, nil
	})

	genkit.DefineBatchEvaluator(g, "custom", "simpleBatchEvaluator", &evalOptions, func(ctx context.Context, req *ai.EvaluatorRequest) (*ai.EvaluatorResponse, error) {
		var evalResponses []ai.EvaluationResult
		dataset := *req.Dataset
		for i := 0; i < len(dataset); i++ {
			input := dataset[i]

			m := make(map[string]any)
			m["reasoning"] = fmt.Sprintf("batch of cookies, %s", input.Input)
			score := ai.Score{
				Id:      "testScore",
				Score:   true,
				Status:  ai.ScoreStatusPass.String(),
				Details: m,
			}
			callbackResponse := ai.EvaluationResult{
				TestCaseId: input.TestCaseId,
				Evaluation: []ai.Score{score},
			}
			evalResponses = append(evalResponses, callbackResponse)
		}
		return &evalResponses, nil
	})

	genkit.DefineFlow(g, "simpleQaFlow", func(ctx context.Context, input *simpleQaInput) (string, error) {
		d1 := ai.DocumentFromText("Paris is the capital of France", nil)
		d2 := ai.DocumentFromText("USA is the largest importer of coffee", nil)
		d3 := ai.DocumentFromText("Water exists in 3 states - solid, liquid and gas", nil)

		err := ai.Index(ctx, indexer, ai.WithIndexerDocs(d1, d2, d3))
		if err != nil {
			return "", err
		}

		dRequest := ai.DocumentFromText(input.Question, nil)
		response, err := ai.Retrieve(ctx, retriever, ai.WithRetrieverDoc(dRequest))
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

		resp, err := simpleQaPrompt.Execute(ctx, ai.WithInput(promptInput))
		if err != nil {
			return "", err
		}
		return resp.Text(), nil
	})

	<-ctx.Done()
}

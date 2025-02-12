// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// This program doesn't do anything interesting.
// It is used by go/tests/api_test.go.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func main() {
	opts := genkit.StartOptions{
		FlowAddr: "127.0.0.1:3400",
	}

	// used for streamed flows
	type chunk struct {
		Count int `json:"count"`
	}

	g, err := genkit.New(nil)
	if err != nil {
		log.Fatal(err)
	}
	model := genkit.DefineModel(g, "", "customReflector", nil, nil, echo)
	genkit.DefineFlow(g, "testFlow", func(ctx context.Context, in string) (string, error) {
		res, err := genkit.Generate(ctx, g, ai.WithModel(model), ai.WithTextPrompt(in))
		if err != nil {
			return "", err
		}
		_ = res
		return "TBD", nil
	})

	genkit.DefineStreamingFlow(g, "streamy", func(ctx context.Context, count int, cb func(context.Context, chunk) error) (string, error) {
		i := 0
		if cb != nil {
			for ; i < count; i++ {
				if err := cb(ctx, chunk{i}); err != nil {
					return "", err
				}
			}
		}
		return fmt.Sprintf("done %d, streamed: %d times", count, i), nil
	})

	if err := g.Start(context.Background(), &opts); err != nil {
		log.Fatal(err)
	}
}

func echo(ctx context.Context, req *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	jsonBytes, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	return &ai.ModelResponse{
		FinishReason: "stop",
		Message: &ai.Message{
			Role:    "model",
			Content: []*ai.Part{ai.NewTextPart(string(jsonBytes))},
		},
	}, nil
}

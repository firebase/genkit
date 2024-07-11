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

// This program doesn't do anything interesting.
// It is used by go/tests/api_test.go.
package main

import (
	"context"
	"encoding/json"
	"log"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func main() {
	model := ai.DefineModel("", "customReflector", nil, echo)
	genkit.DefineFlow("testFlow", func(ctx context.Context, in string) (string, error) {
		res, err := model.Generate(ctx, ai.NewGenerateRequest(nil, ai.NewUserTextMessage(in)), nil)
		if err != nil {
			return "", err
		}
		_ = res
		return "TBD", nil
	})
	if err := genkit.Init(context.Background(), nil); err != nil {
		log.Fatal(err)
	}
}

func echo(ctx context.Context, req *ai.GenerateRequest, cb func(context.Context, *ai.GenerateResponseChunk) error) (*ai.GenerateResponse, error) {
	jsonBytes, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	return &ai.GenerateResponse{
		Candidates: []*ai.Candidate{{
			Index:        0,
			FinishReason: "stop",
			Message: &ai.Message{
				Role:    "model",
				Content: []*ai.Part{ai.NewTextPart(string(jsonBytes))},
			},
		}},
	}, nil
}

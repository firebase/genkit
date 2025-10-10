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

package ai

import (
	"context"
	"errors"
	"fmt"
	"testing"

	"github.com/firebase/genkit/go/internal/registry"
)

var testEvalFunc = func(ctx context.Context, req *EvaluatorCallbackRequest) (*EvaluatorCallbackResponse, error) {
	m := make(map[string]any)
	m["reasoning"] = "No good reason"
	m["options"] = req.Options
	score := Score{
		Id:      "testScore",
		Score:   1,
		Status:  ScoreStatusPass.String(),
		Details: m,
	}
	callbackResponse := EvaluatorCallbackResponse{
		TestCaseId: req.Input.TestCaseId,
		Evaluation: []Score{score},
	}
	return &callbackResponse, nil
}

var testBatchEvalFunc = func(ctx context.Context, req *EvaluatorRequest) (*EvaluatorResponse, error) {
	var evalResponses []EvaluationResult
	for _, datapoint := range req.Dataset {
		fmt.Printf("%+v\n", datapoint)
		m := make(map[string]any)
		m["reasoning"] = fmt.Sprintf("batch of cookies, %s", datapoint.Input)
		m["options"] = req.Options
		score := Score{
			Id:      "testScore",
			Score:   true,
			Status:  ScoreStatusPass.String(),
			Details: m,
		}
		callbackResponse := EvaluationResult{
			TestCaseId: datapoint.TestCaseId,
			Evaluation: []Score{score},
		}
		evalResponses = append(evalResponses, callbackResponse)
	}
	return &evalResponses, nil
}

var testFailingEvalFunc = func(ctx context.Context, req *EvaluatorCallbackRequest) (*EvaluatorCallbackResponse, error) {
	return nil, errors.New("i give up")
}

var evalOpts = EvaluatorOptions{
	DisplayName: "Test Evaluator",
	Definition:  "Returns pass score for all",
	IsBilled:    false,
}

var dataset = []*Example{
	{
		Input: "hello world",
	},
	{
		Input: "Foo bar",
	},
}

var testRequest = EvaluatorRequest{
	Dataset:      dataset,
	EvaluationId: "testrun",
	Options:      "test-options",
}

func TestSimpleEvaluator(t *testing.T) {
	r := registry.New()

	evaluator := DefineEvaluator(r, "test/testEvaluator", &evalOpts, testEvalFunc)

	resp, err := evaluator.Evaluate(context.Background(), &testRequest)
	if err != nil {
		t.Fatal(err)
	}

	if got, want := len(*resp), 2; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Id, "testScore"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Score, 1; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Status, "PASS"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Details["options"], "test-options"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestOptionsRequired(t *testing.T) {
	r := registry.New()

	_ = DefineEvaluator(r, "test/testEvaluator", &evalOpts, testEvalFunc)
	_ = DefineBatchEvaluator(r, "test/testBatchEvaluator", &evalOpts, testBatchEvalFunc)
}

func TestFailingEvaluator(t *testing.T) {
	r := registry.New()

	evalAction := DefineEvaluator(r, "test/testEvaluator", &evalOpts, testFailingEvalFunc)

	resp, err := evalAction.Evaluate(context.Background(), &testRequest)
	if err != nil {
		t.Fatal(err)
	}

	if got, dontWant := (*resp)[0].Evaluation[0].Error, ""; got == dontWant {
		t.Errorf("got %v, dontWant %v", got, dontWant)
	}
	if got, want := (*resp)[0].Evaluation[0].Status, "FAIL"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestLookupEvaluator(t *testing.T) {
	r := registry.New()

	DefineEvaluator(r, "test/testEvaluator", &evalOpts, testEvalFunc)
	DefineBatchEvaluator(r, "test/testBatchEvaluator", &evalOpts, testBatchEvalFunc)

	if LookupEvaluator(r, "test/testEvaluator") == nil {
		t.Errorf("LookupEvaluator(r, \"test/testEvaluator\") is nil")
	}
	if LookupEvaluator(r, "test/testBatchEvaluator") == nil {
		t.Errorf("LookupEvaluator(r, \"test/testBatchEvaluator\") is nil")
	}
}

func TestEvaluate(t *testing.T) {
	r := registry.New()

	evalAction := DefineEvaluator(r, "test/testEvaluator", &evalOpts, testEvalFunc)

	resp, err := Evaluate(context.Background(), r,
		WithEvaluator(evalAction),
		WithDataset(dataset...),
		WithID("testrun"),
		WithConfig("test-options"))
	if err != nil {
		t.Fatal(err)
	}

	if got, want := (*resp)[0].Evaluation[0].Id, "testScore"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Score, 1; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Status, "PASS"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Details["options"], "test-options"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestBatchEvaluator(t *testing.T) {
	r := registry.New()

	evalAction := DefineBatchEvaluator(r, "test/testBatchEvaluator", &evalOpts, testBatchEvalFunc)

	resp, err := evalAction.Evaluate(context.Background(), &testRequest)
	if err != nil {
		t.Fatal(err)
	}

	if got, want := len(*resp), 2; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Id, "testScore"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Score, true; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Status, "PASS"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
	if got, want := (*resp)[0].Evaluation[0].Details["options"], "test-options"; got != want {
		t.Errorf("got %v, want %v", got, want)
	}
}

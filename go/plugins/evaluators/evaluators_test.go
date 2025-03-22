package evaluators_test

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/evaluators"
)

func TestEvaluators(t *testing.T) {
	ctx := context.Background()
	g, err := genkit.Init(ctx)
	if err != nil {
		t.Fatal(err)
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
		t.Fatal(err)
	}

	t.Run("deep equal", func(t *testing.T) {
		var dataset = ai.Dataset{
			{
				Input:     "sample",
				Reference: "hello world",
				Output:    "hello world",
			},
			{
				Input:     "sample",
				Output:    "Foo bar",
				Reference: "gablorken",
			},
			{
				Input:  "sample",
				Output: "Foo bar",
			},
		}
		var testRequest = ai.EvaluatorRequest{
			Dataset:      &dataset,
			EvaluationId: "testrun",
		}

		evalAction := genkit.LookupEvaluator(g, "genkitEval", "deep_equal")
		resp, err := evalAction.Evaluate(ctx, &testRequest)
		if err != nil {
			t.Fatal(err)
		}
		if got, want := (*resp)[0].Evaluation[0].Score, true; got != want {
			t.Errorf("got %v, want %v", got, want)
		}
		if got, want := (*resp)[1].Evaluation[0].Score, false; got != want {
			t.Errorf("got %v, want %v", got, want)
		}
		if got := (*resp)[2].Evaluation[0].Error; got == "" {
			t.Errorf("got %v, want error", got)
		}
	})

	t.Run("regex", func(t *testing.T) {
		var dataset = ai.Dataset{
			{
				Input:     "sample",
				Reference: "ba?a?a",
				Output:    "banana",
			},
			{
				Input:     "sample",
				Reference: "ba?a?a",
				Output:    "apple",
			},
			{
				Input:     "sample",
				Reference: 12345,
				Output:    "apple",
			},
		}
		var testRequest = ai.EvaluatorRequest{
			Dataset:      &dataset,
			EvaluationId: "testrun",
		}

		evalAction := genkit.LookupEvaluator(g, "genkitEval", "regex")
		resp, err := evalAction.Evaluate(ctx, &testRequest)
		if err != nil {
			t.Fatal(err)
		}
		if got, want := (*resp)[0].Evaluation[0].Score, true; got != want {
			t.Errorf("got %v, want %v", got, want)
		}
		if got, want := (*resp)[1].Evaluation[0].Score, false; got != want {
			t.Errorf("got %v, want %v", got, want)
		}
		if got := (*resp)[2].Evaluation[0].Error; got == "" {
			t.Errorf("got %v, want error", got)
		}
	})

	t.Run("jsonata", func(t *testing.T) {
		var dataset = ai.Dataset{
			{
				Input:     "sample",
				Reference: "age=33",
				Output: map[string]any{
					"name": "Bob",
					"age":  33,
				},
			},
			{
				Input:     "sample",
				Reference: "age=31",
				Output: map[string]any{
					"name": "Bob",
					"age":  33,
				},
			},
			{
				Input:     "sample",
				Reference: 123456,
				Output: map[string]any{
					"name": "Bob",
					"age":  33,
				},
			},
		}
		var testRequest = ai.EvaluatorRequest{
			Dataset:      &dataset,
			EvaluationId: "testrun",
		}

		evalAction := genkit.LookupEvaluator(g, "genkitEval", "jsonata")
		resp, err := evalAction.Evaluate(ctx, &testRequest)
		if err != nil {
			t.Fatal(err)
		}
		if got, want := (*resp)[0].Evaluation[0].Score, true; got != want {
			t.Errorf("got %v, want %v", got, want)
		}
		if got, want := (*resp)[1].Evaluation[0].Score, false; got != want {
			t.Errorf("got %v, want %v", got, want)
		}
		if got := (*resp)[2].Evaluation[0].Error; got == "" {
			t.Errorf("got %v, want error", got)
		}
	})
}

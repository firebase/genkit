// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package evaluators defines a set of Genkit Evaluators for popular use-cases
package evaluators

import (
	"context"
	"errors"
	"fmt"
	"reflect"
	"regexp"
	"sync"

	jsonata "github.com/blues/jsonata-go"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/genkit"
)

const provider = "genkitEval"

// EvaluatorType is an enum used to indicate the type of evaluator being
// configured for use
type EvaluatorType int

const (
	EvaluatorTypeDeepEqual EvaluatorType = iota
	EvaluatorTypeRegex
	EvaluatorTypeJsonata
)

var evaluatorTypeName = map[EvaluatorType]string{
	EvaluatorTypeDeepEqual: "DEEP_EQUAL",
	EvaluatorTypeRegex:     "REGEX",
	EvaluatorTypeJsonata:   "JSONATA",
}

func (ss EvaluatorType) String() string {
	return evaluatorTypeName[ss]
}

// MetricConfig provides configuration options for a specific metric. More
// Params (judge LLMs, etc.) could be configured by extending this struct
type MetricConfig struct {
	MetricType EvaluatorType
}

// Config provides configuration options for the Init function.
type Config struct {
	Metrics []MetricConfig
}

var state struct {
	config  *Config
	initted bool
	mu      sync.Mutex
}

// Init initializes the plugin.
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) (err error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("genkitEval.Init already called")
	}
	if cfg == nil || len(cfg.Metrics) == 0 {
		return errors.New("genkitEval: need to configure at least one metric")
	}
	state.config = cfg
	state.initted = true

	for _, metric := range state.config.Metrics {
		ConfigureMetric(g, metric)
	}
	return nil

	return nil
}

func ConfigureMetric(g *genkit.Genkit, metric MetricConfig) (ai.Evaluator, error) {
	switch metric.MetricType {
	case EvaluatorTypeDeepEqual:
		return configureDeepEqualEvaluator(g)
	case EvaluatorTypeJsonata:
		return configureJsonataEvaluator(g)
	case EvaluatorTypeRegex:
		return configureRegexEvaluator(g)
	default:
		panic(fmt.Sprintf("Unsupported genkitEval metric type: %s", metric.MetricType.String()))
	}
}

func configureRegexEvaluator(g *genkit.Genkit) (ai.Evaluator, error) {
	evalOptions := ai.EvaluatorOptions{
		DisplayName: "RegExp",
		Definition:  "Tests output against the regexp provided as reference",
		IsBilled:    false,
	}
	evaluator, err := genkit.DefineEvaluator(g, provider, "regex", &evalOptions, func(ctx context.Context, req *ai.EvaluatorCallbackRequest) (*ai.EvaluatorCallbackResponse, error) {
		dataPoint := req.Input
		var score ai.Score
		if dataPoint.Output == nil {
			return nil, errors.New("output was not provided")
		}
		if dataPoint.Reference == nil {
			return nil, errors.New("reference was not provided")
		}
		if reflect.TypeOf(dataPoint.Reference).String() != "string" {
			return nil, errors.New("reference must be a string (regex)")
		}
		if reflect.TypeOf(dataPoint.Output).String() == "string" {
			// Test against provided regexp
			match, _ := regexp.MatchString((dataPoint.Reference).(string), (dataPoint.Output).(string))
			status := ai.ScoreStatusUnknown
			if match {
				status = ai.ScoreStatusPass
			} else {
				status = ai.ScoreStatusFail
			}
			score = ai.Score{
				Score:  match,
				Status: status.String(),
			}
		} else {
			// Mark as failed if output is not string type
			logger.FromContext(ctx).Debug("genkitEval",
				"regex", fmt.Sprintf("Failed regex evaluation, as output is not string type. TestCaseId: %s", dataPoint.TestCaseId))
			score = ai.Score{
				Score:  false,
				Status: ai.ScoreStatusFail.String(),
			}
		}
		callbackResponse := ai.EvaluatorCallbackResponse{
			TestCaseId: req.Input.TestCaseId,
			Evaluation: []ai.Score{score},
		}
		return &callbackResponse, nil
	})
	if err != nil {
		return nil, err
	}
	return evaluator, nil
}

func configureDeepEqualEvaluator(g *genkit.Genkit) (ai.Evaluator, error) {
	evalOptions := ai.EvaluatorOptions{
		DisplayName: "Deep Equal",
		Definition:  "Tests equality of output against the provided reference",
		IsBilled:    false,
	}
	evaluator, err := genkit.DefineEvaluator(g, provider, "deep_equal", &evalOptions, func(ctx context.Context, req *ai.EvaluatorCallbackRequest) (*ai.EvaluatorCallbackResponse, error) {
		dataPoint := req.Input
		var score ai.Score
		if dataPoint.Output == nil {
			return nil, errors.New("output was not provided")
		}
		if dataPoint.Reference == nil {
			return nil, errors.New("reference was not provided")
		}
		deepEqual := reflect.DeepEqual(dataPoint.Reference, dataPoint.Output)
		status := ai.ScoreStatusUnknown
		if deepEqual {
			status = ai.ScoreStatusPass
		} else {
			status = ai.ScoreStatusFail
		}
		score = ai.Score{
			Score:  deepEqual,
			Status: status.String(),
		}

		callbackResponse := ai.EvaluatorCallbackResponse{
			TestCaseId: req.Input.TestCaseId,
			Evaluation: []ai.Score{score},
		}
		return &callbackResponse, nil
	})
	if err != nil {
		return nil, err
	}
	return evaluator, nil
}

func configureJsonataEvaluator(g *genkit.Genkit) (ai.Evaluator, error) {
	evalOptions := ai.EvaluatorOptions{
		DisplayName: "JSONata",
		Definition:  "Tests JSONata expression (provided in reference) against output",
		IsBilled:    false,
	}
	evaluator, err := genkit.DefineEvaluator(g, provider, "jsonata", &evalOptions, func(ctx context.Context, req *ai.EvaluatorCallbackRequest) (*ai.EvaluatorCallbackResponse, error) {
		dataPoint := req.Input
		var score ai.Score
		if dataPoint.Output == nil {
			return nil, errors.New("output was not provided")
		}
		if dataPoint.Reference == nil {
			return nil, errors.New("reference was not provided")
		}
		if reflect.TypeOf(dataPoint.Reference).String() != "string" {
			return nil, errors.New("reference must be a string (jsonata)")
		}
		// Test against provided jsonata
		exp := jsonata.MustCompile((dataPoint.Reference).(string))
		res, err := exp.Eval(dataPoint.Output)
		if err != nil {
			return nil, err
		}
		status := ai.ScoreStatusUnknown
		if res != nil || res != "" {
			status = ai.ScoreStatusPass
		} else {
			status = ai.ScoreStatusFail
		}
		score = ai.Score{
			Score:  res,
			Status: status.String(),
		}

		callbackResponse := ai.EvaluatorCallbackResponse{
			TestCaseId: req.Input.TestCaseId,
			Evaluation: []ai.Score{score},
		}
		return &callbackResponse, nil
	})
	if err != nil {
		return nil, err
	}
	return evaluator, nil
}

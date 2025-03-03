// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"errors"
	"fmt"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/google/uuid"
)

// Evaluator represents a evaluator action.
type Evaluator interface {
	// Name returns the name of the evaluator.
	Name() string
	// Evaluates a dataset.
	Evaluate(ctx context.Context, req *EvaluatorRequest) (*EvaluatorResponse, error)
}

type (
	evaluatorActionDef core.Action[*EvaluatorRequest, *EvaluatorResponse, struct{}]

	evaluatorAction = core.Action[*EvaluatorRequest, *EvaluatorResponse, struct{}]
)

// Example is a single example that requires evaluation
type Example struct {
	TestCaseId string   `json:"testCaseId,omitempty"`
	Input      any      `json:"input"`
	Output     any      `json:"output,omitempty"`
	Context    any      `json:"context,omitempty"`
	Reference  any      `json:"reference,omitempty"`
	TraceIds   []string `json:"traceIds,omitempty"`
}

type Dataset = []Example

// EvaluatorRequest is the data we pass to evaluate a dataset.
// The Options field is specific to the actual evaluator implementation.
type EvaluatorRequest struct {
	Dataset      []Example `json:"dataset"`
	EvaluationId string    `json:"evalRunId"`
	Options      any       `json:"options,omitempty"`
}

type ScoreStatus int

const (
	Unknown ScoreStatus = iota
	Fail
	Pass
)

var statusName = map[ScoreStatus]string{
	Unknown: "unknown",
	Fail:    "fail",
	Pass:    "pass",
}

func (ss ScoreStatus) String() string {
	return statusName[ss]
}

type Score struct {
	Id      string         `json:"id,omitempty"`
	Score   any            `json:"score,omitempty"`
	Error   string         `json:"error,omitempty"`
	Details map[string]any `json:"details,omitempty"`
}

type EvaluationResult struct {
	TestCaseId string  `json:"testCaseId"`
	TraceId    string  `json:"traceId,omitempty"`
	SpanId     string  `json:"spanId,omitempty"`
	Evaluation []Score `json:"score"`
}

type EvaluatorResponse = []EvaluationResult

type EvaluatorOptions struct {
	DisplayName string `json:"displayName"`
	Definition  string `json:"definition"`
	IsBilled    bool   `json:"isBilled,omitempty"`
}

// EvaluatorRequest is the data we pass to evaluate a dataset.
// The Options field is specific to the actual evaluator implementation.
type EvaluatorCallbackRequest struct {
	Input   Example `json:"input"`
	Options any     `json:"options,omitempty"`
}

type EvaluatorCallbackResponse = EvaluationResult

// DefineEvaluator registers the given evaluator function as an action, and
// returns a [Evaluator] that runs it.
func DefineEvaluator(r *registry.Registry, provider, name string, options *EvaluatorOptions, eval func(context.Context, *EvaluatorCallbackRequest) (*EvaluatorCallbackResponse, error)) *evaluatorActionDef {
	metadataMap := map[string]any{}
	metadataMap["evaluatorIsBilled"] = options.IsBilled
	metadataMap["evaluatorDisplayName"] = options.DisplayName
	metadataMap["evaluatorDefinition"] = options.Definition

	return (*evaluatorActionDef)(core.DefineAction(r, provider, name, atype.Evaluator, metadataMap, func(ctx context.Context, req *EvaluatorRequest) (output *EvaluatorResponse, err error) {
		var evalResponses []EvaluationResult
		dataset := req.Dataset
		for i := 0; i < len(dataset); i++ {
			datapoint := dataset[i]
			if datapoint.TestCaseId == "" {
				datapoint.TestCaseId = uuid.New().String()
			}
			_, err := tracing.RunInNewSpan(ctx, r.TracingState(), fmt.Sprintf("TestCase %s", datapoint.TestCaseId), "evaluator", false, datapoint,
				func(ctx context.Context, input Example) (*EvaluatorCallbackResponse, error) {
					spanMetadata := tracing.SpanMetadata(ctx)
					spanMetadata.Input = input
					callbackRequest := EvaluatorCallbackRequest{
						Input:   input,
						Options: req.Options,
					}
					evaluatorResponse, err := eval(ctx, &callbackRequest)
					if err != nil {
						failedScore := Score{
							// Status: Fail,
							Error: fmt.Sprintf("Evaluation of test case %s failed: \n %s", input.TestCaseId, err.Error()),
						}
						failedEvalResult := EvaluationResult{
							TestCaseId: input.TestCaseId,
							Evaluation: []Score{failedScore},
						}
						evalResponses = append(evalResponses, failedEvalResult)
						return nil, err
					}
					spanMetadata.Output = evaluatorResponse
					evalResponses = append(evalResponses, *evaluatorResponse)
					return evaluatorResponse, nil
				})
			if err != nil {
				logger.FromContext(ctx).Debug("EvaluatorAction", "err", err)
				continue
			}
		}
		return &evalResponses, nil
	}))
}

// IsDefinedEvaluator reports whether an [Evaluator] is defined.
func IsDefinedEvaluator(r *registry.Registry, provider, name string) bool {
	return (*evaluatorActionDef)(core.LookupActionFor[*EvaluatorRequest, *EvaluatorResponse, struct{}](r, atype.Evaluator, provider, name)) != nil
}

// LookupEvaluator looks up an [Evaluator] registered by [DefineEvaluator].
// It returns nil if the evaluator was not defined.
func LookupEvaluator(r *registry.Registry, provider, name string) Evaluator {
	return (*evaluatorActionDef)(core.LookupActionFor[*EvaluatorRequest, *EvaluatorResponse, struct{}](r, atype.Evaluator, provider, name))
}

// Evaluate runs the given [Evaluator].
func (e *evaluatorActionDef) Evaluate(ctx context.Context, req *EvaluatorRequest) (*EvaluatorResponse, error) {
	if e == nil {
		return nil, errors.New("Evaluator called on a nil Evaluator; check that all evaluators are defined")
	}
	a := (*core.Action[*EvaluatorRequest, *EvaluatorResponse, struct{}])(e)
	return a.Run(ctx, req, nil)
}

// EvaluateOption configures params of the Embed call.
type EvaluateOption func(req *EvaluatorRequest) error

// WithEvaluateDataset set the dataset on [EvaluatorRequest]
func WithEvaluateDataset(dataset Dataset) EvaluateOption {
	return func(req *EvaluatorRequest) error {
		req.Dataset = dataset
		return nil
	}
}

// WithEvaluateId set evaluation ID on [EvaluatorRequest]
func WithEvaluateId(evaluationId string) EvaluateOption {
	return func(req *EvaluatorRequest) error {
		req.EvaluationId = evaluationId
		return nil
	}
}

// WithEvaluateOptions set evaluator options on [EvaluatorRequest]
func WithEvaluateOptions(opts any) EvaluateOption {
	return func(req *EvaluatorRequest) error {
		req.Options = opts
		return nil
	}
}

// Evaluate calls the retrivers with provided options.
func Evaluate(ctx context.Context, r Evaluator, opts ...EvaluateOption) (*EvaluatorResponse, error) {
	req := &EvaluatorRequest{}
	for _, with := range opts {
		err := with(req)
		if err != nil {
			return nil, err
		}
	}
	return r.Evaluate(ctx, req)
}

func (r *evaluatorActionDef) Name() string { return (*evaluatorAction)(r).Name() }

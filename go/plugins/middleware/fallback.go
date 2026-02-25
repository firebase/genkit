// Copyright 2026 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package middleware

import (
	"context"
	"encoding/json"
	"errors"
	"slices"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
)

// defaultFallbackStatuses are the status codes that trigger a fallback by default.
var defaultFallbackStatuses = []core.StatusName{
	core.UNAVAILABLE,
	core.DEADLINE_EXCEEDED,
	core.RESOURCE_EXHAUSTED,
	core.ABORTED,
	core.INTERNAL,
	core.NOT_FOUND,
	core.UNIMPLEMENTED,
}

// Fallback is a middleware that tries alternative models when the primary model
// fails with a retryable error status.
//
// It only hooks the Model stage — when a model API call fails with a matching
// status, the request is forwarded to the next model in the list.
//
// Models are specified as [ai.ModelArg] values (model references, model instances,
// or strings via [ai.NewModelRef]) and resolved via the [genkit.Genkit] instance at call time.
// The Genkit instance is available via [genkit.FromContext] during generation.
//
// Usage:
//
//	resp, err := genkit.Generate(ctx, g,
//	    ai.WithModel(primary),
//	    ai.WithPrompt("hello"),
//	    ai.WithUse(&middleware.Fallback{Models: []ai.ModelArg{backup1, backup2}}),
//	)
type Fallback struct {
	ai.BaseMiddleware
	// Models is the ordered list of fallback models to try.
	// Each entry is an [ai.ModelArg] (e.g. an [ai.Model], [ai.ModelRef], etc.).
	// These are tried in order after the primary model fails.
	Models ModelList `json:"models,omitempty"`
	// Statuses is the set of status codes that trigger a fallback.
	// Only [core.GenkitError] errors with a matching status will trigger fallback;
	// non-GenkitError errors propagate immediately.
	// Defaults to [defaultFallbackStatuses].
	Statuses []core.StatusName `json:"statuses,omitempty"`
}

// ModelList is a list of [ai.ModelArg] values that marshals to/from JSON as
// a list of model name strings.
type ModelList []ai.ModelArg

func (l ModelList) MarshalJSON() ([]byte, error) {
	names := make([]string, len(l))
	for i, m := range l {
		names[i] = m.Name()
	}
	return json.Marshal(names)
}

func (l *ModelList) UnmarshalJSON(data []byte) error {
	var names []string
	if err := json.Unmarshal(data, &names); err != nil {
		return err
	}
	*l = make(ModelList, len(names))
	for i, name := range names {
		(*l)[i] = ai.NewModelRef(name, nil)
	}
	return nil
}

func (f *Fallback) Name() string { return provider + "/fallback" }

func (f *Fallback) New() ai.Middleware {
	return &Fallback{
		Models:   f.Models,
		Statuses: f.Statuses,
	}
}

func (f *Fallback) statuses() []core.StatusName {
	if len(f.Statuses) > 0 {
		return f.Statuses
	}
	return defaultFallbackStatuses
}

func (f *Fallback) WrapModel(ctx context.Context, params *ai.ModelParams, next ai.ModelNext) (*ai.ModelResponse, error) {
	resp, err := next(ctx, params)
	if err == nil {
		return resp, nil
	}

	if !isFallbackRetryable(err, f.statuses()) {
		return nil, err
	}

	lastErr := err
	for _, ref := range f.Models {
		name := ref.Name()
		m := genkit.LookupModel(genkit.FromContext(ctx), name)
		if m == nil {
			return nil, core.NewError(core.NOT_FOUND, "fallback: model %q not found", name)
		}
		resp, err := m.Generate(ctx, params.Request, params.Callback)
		if err == nil {
			return resp, nil
		}
		lastErr = err
		if !isFallbackRetryable(err, f.statuses()) {
			return nil, err
		}
	}
	return nil, lastErr
}

// isFallbackRetryable reports whether err should trigger trying the next model.
// Only GenkitErrors with a matching status trigger fallback.
func isFallbackRetryable(err error, statuses []core.StatusName) bool {
	var ge *core.GenkitError
	if !errors.As(err, &ge) {
		return false
	}
	return slices.Contains(statuses, ge.Status)
}

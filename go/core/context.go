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
//
// SPDX-License-Identifier: Apache-2.0

package core

import (
	"context"
	"encoding/json"

	"github.com/firebase/genkit/go/internal/base"
)

var actionCtxKey = base.NewContextKey[int]()

// WithActionContext returns a new Context with Action runtime context (side channel data) value set.
func WithActionContext(ctx context.Context, actionCtx ActionContext) context.Context {
	return context.WithValue(ctx, actionCtxKey, actionCtx)
}

// FromContext returns the Action runtime context (side channel data) from context.
func FromContext(ctx context.Context) ActionContext {
	val := ctx.Value(actionCtxKey)
	if val == nil {
		return nil
	}
	return val.(ActionContext)
}

// ActionContext is the runtime context for an Action.
type ActionContext = map[string]any

// RequestData is the data associated with a request.
// It is used to provide additional context to the Action.
type RequestData struct {
	Method  string            // Method is the HTTP method of the request (e.g. "GET", "POST", etc.)
	Headers map[string]string // Headers is the headers of the request. The keys are the header names in lowercase.
	Input   json.RawMessage   // Input is the body of the request.
}

// ContextProvider is a function that returns an ActionContext for a given request.
// It is used to provide additional context to the Action.
type ContextProvider = func(ctx context.Context, req RequestData) (ActionContext, error)

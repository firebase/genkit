// Copyright 2024 Google LLC
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

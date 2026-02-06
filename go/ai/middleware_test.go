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

package ai

import (
	"context"
	"sync/atomic"
	"testing"
)

// testMiddleware is a simple middleware for testing that tracks hook invocations.
type testMiddleware struct {
	BaseMiddleware
	Label         string `json:"label"`
	generateCalls int
	modelCalls    int
	toolCalls     int32 // atomic since tool hooks run in parallel
}

func (m *testMiddleware) Name() string { return "test" }

func (m *testMiddleware) New() Middleware {
	return &testMiddleware{Label: m.Label}
}

func (m *testMiddleware) Generate(ctx context.Context, state *GenerateState, next GenerateNext) (*ModelResponse, error) {
	m.generateCalls++
	return next(ctx, state)
}

func (m *testMiddleware) Model(ctx context.Context, state *ModelState, next ModelNext) (*ModelResponse, error) {
	m.modelCalls++
	return next(ctx, state)
}

func (m *testMiddleware) Tool(ctx context.Context, state *ToolState, next ToolNext) (*ToolResponse, error) {
	atomic.AddInt32(&m.toolCalls, 1)
	return next(ctx, state)
}

func TestNewMiddleware(t *testing.T) {
	proto := &testMiddleware{Label: "original"}
	desc := NewMiddleware("test middleware", proto)

	if desc.Name != "test" {
		t.Errorf("got name %q, want %q", desc.Name, "test")
	}
	if desc.Description != "test middleware" {
		t.Errorf("got description %q, want %q", desc.Description, "test middleware")
	}
}

func TestDefineAndLookupMiddleware(t *testing.T) {
	r := newTestRegistry(t)
	proto := &testMiddleware{Label: "original"}
	DefineMiddleware(r, "test middleware", proto)

	found := LookupMiddleware(r, "test")
	if found == nil {
		t.Fatal("expected to find middleware, got nil")
	}
	if found.Name != "test" {
		t.Errorf("got name %q, want %q", found.Name, "test")
	}
}

func TestLookupMiddlewareNotFound(t *testing.T) {
	r := newTestRegistry(t)
	found := LookupMiddleware(r, "nonexistent")
	if found != nil {
		t.Errorf("expected nil, got %v", found)
	}
}

func TestConfigFromJSON(t *testing.T) {
	proto := &testMiddleware{Label: "stable"}
	desc := NewMiddleware("test middleware", proto)

	handler, err := desc.configFromJSON([]byte(`{"label": "custom"}`))
	if err != nil {
		t.Fatalf("configFromJSON failed: %v", err)
	}

	tm, ok := handler.(*testMiddleware)
	if !ok {
		t.Fatalf("expected *testMiddleware, got %T", handler)
	}
	if tm.Label != "custom" {
		t.Errorf("got label %q, want %q", tm.Label, "custom")
	}
	// Per-request state should be zeroed by New()
	if tm.generateCalls != 0 {
		t.Errorf("got generateCalls %d, want 0", tm.generateCalls)
	}
}

func TestConfigFromJSONPreservesStableState(t *testing.T) {
	// Simulate a plugin middleware with unexported stable state
	proto := &stableStateMiddleware{apiKey: "secret123"}
	desc := NewMiddleware("middleware with stable state", proto)

	handler, err := desc.configFromJSON([]byte(`{"sampleRate": 0.5}`))
	if err != nil {
		t.Fatalf("configFromJSON failed: %v", err)
	}

	sm, ok := handler.(*stableStateMiddleware)
	if !ok {
		t.Fatalf("expected *stableStateMiddleware, got %T", handler)
	}
	if sm.apiKey != "secret123" {
		t.Errorf("got apiKey %q, want %q", sm.apiKey, "secret123")
	}
	if sm.SampleRate != 0.5 {
		t.Errorf("got SampleRate %f, want 0.5", sm.SampleRate)
	}
}

func TestMiddlewareModelHook(t *testing.T) {
	r := newTestRegistry(t)
	m := defineFakeModel(t, r, fakeModelConfig{})
	DefineMiddleware(r, "tracks calls", &testMiddleware{})

	resp, err := Generate(ctx, r,
		WithModel(m),
		WithPrompt("hello"),
		WithUse(&testMiddleware{}),
	)
	assertNoError(t, err)
	if resp == nil {
		t.Fatal("expected response, got nil")
	}
}

func TestMiddlewareToolHook(t *testing.T) {
	r := newTestRegistry(t)
	defineFakeModel(t, r, fakeModelConfig{
		name:    "test/toolModel",
		handler: toolCallingModelHandler("myTool", map[string]any{"value": "test"}, "done"),
	})
	defineFakeTool(t, r, "myTool", "A test tool")

	mw := &testMiddleware{}
	DefineMiddleware(r, "tracks calls", mw)

	_, err := Generate(ctx, r,
		WithModelName("test/toolModel"),
		WithPrompt("use the tool"),
		WithTools(ToolName("myTool")),
		WithUse(&testMiddleware{}),
	)
	assertNoError(t, err)
}

func TestMiddlewareOrdering(t *testing.T) {
	// First middleware is outermost
	var order []string
	r := newTestRegistry(t)
	m := defineFakeModel(t, r, fakeModelConfig{})

	mwA := &orderMiddleware{label: "A", order: &order}
	mwB := &orderMiddleware{label: "B", order: &order}
	DefineMiddleware(r, "middleware A", mwA)
	DefineMiddleware(r, "middleware B", mwB)

	_, err := Generate(ctx, r,
		WithModel(m),
		WithPrompt("hello"),
		WithUse(
			&orderMiddleware{label: "A", order: &order},
			&orderMiddleware{label: "B", order: &order},
		),
	)
	assertNoError(t, err)

	// Expect: A-before, B-before, B-after, A-after (first is outermost)
	want := []string{"A-model-before", "B-model-before", "B-model-after", "A-model-after"}
	if len(order) != len(want) {
		t.Fatalf("got order %v, want %v", order, want)
	}
	for i := range want {
		if order[i] != want[i] {
			t.Errorf("order[%d] = %q, want %q", i, order[i], want[i])
		}
	}
}

// --- helper middleware types for tests ---

// stableStateMiddleware has unexported stable state preserved by New().
type stableStateMiddleware struct {
	BaseMiddleware
	SampleRate float64 `json:"sampleRate"`
	apiKey     string
}

func (m *stableStateMiddleware) Name() string { return "stableState" }

func (m *stableStateMiddleware) New() Middleware {
	return &stableStateMiddleware{apiKey: m.apiKey}
}

// orderMiddleware tracks the order of Model hook invocations.
type orderMiddleware struct {
	BaseMiddleware
	label string
	order *[]string
}

func (m *orderMiddleware) Name() string { return "order-" + m.label }

func (m *orderMiddleware) New() Middleware {
	return &orderMiddleware{label: m.label, order: m.order}
}

func (m *orderMiddleware) Model(ctx context.Context, state *ModelState, next ModelNext) (*ModelResponse, error) {
	*m.order = append(*m.order, m.label+"-model-before")
	resp, err := next(ctx, state)
	*m.order = append(*m.order, m.label+"-model-after")
	return resp, err
}

var ctx = context.Background()

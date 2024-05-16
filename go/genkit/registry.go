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

package genkit

import (
	"context"
	"fmt"
	"log"
	"log/slog"
	"slices"
	"sync"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"golang.org/x/exp/maps"
)

// This file implements registries of actions and other values.

// The global registry, used in non-test code.
// A test may create their own registries to avoid conflicting with other tests.
var globalRegistry *registry

func init() {
	// Initialize the global registry, along with a dev tracer, at program startup.
	var err error
	globalRegistry, err = newRegistry()
	if err != nil {
		log.Fatal(err)
	}
}

type registry struct {
	tstate  *tracingState
	mu      sync.Mutex
	actions map[string]action
	// TraceStores, at most one for each [Environment].
	// Only the prod trace store is actually registered; the dev one is
	// always created automatically. But it's simpler if we keep them together here.
	traceStores map[Environment]TraceStore
}

func newRegistry() (*registry, error) {
	r := &registry{
		actions:     map[string]action{},
		traceStores: map[Environment]TraceStore{},
	}
	tstore, err := newDevTraceStore()
	if err != nil {
		return nil, err
	}
	r.registerTraceStore(EnvironmentDev, tstore)
	r.tstate = newTracingState()
	r.tstate.addTraceStoreImmediate(tstore)
	return r, nil
}

// An Environment is the development context that the program is running in.
type Environment string

const (
	EnvironmentDev  Environment = "dev"  // development: testing, debugging, etc.
	EnvironmentProd Environment = "prod" // production: user data, SLOs, etc.
)

// An ActionType is the kind of an action.
type ActionType string

const (
	ActionTypeChatLLM   ActionType = "chat-llm"
	ActionTypeTextLLM   ActionType = "text-llm"
	ActionTypeRetriever ActionType = "retriever"
	ActionTypeIndexer   ActionType = "indexer"
	ActionTypeEmbedder  ActionType = "embedder"
	ActionTypeEvaluator ActionType = "evaluator"
	ActionTypeFlow      ActionType = "flow"
	ActionTypeModel     ActionType = "model"
	ActionTypePrompt    ActionType = "prompt"
	ActionTypeTool      ActionType = "tool"
)

// RegisterAction records the action in the global registry.
// It panics if an action with the same type, provider and name is already
// registered.
func RegisterAction(typ ActionType, provider string, a action) {
	globalRegistry.registerAction(typ, provider, a)
	slog.Info("RegisterAction",
		"type", typ,
		"provider", provider,
		"name", a.Name())
}

func (r *registry) registerAction(typ ActionType, provider string, a action) {
	key := fmt.Sprintf("/%s/%s/%s", typ, provider, a.Name())
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.actions[key]; ok {
		panic(fmt.Sprintf("action %q is already registered", key))
	}
	a.setTracingState(r.tstate)
	r.actions[key] = a
}

// lookupAction returns the action for the given key, or nil if there is none.
func (r *registry) lookupAction(key string) action {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.actions[key]
}

// LookupAction returns the action for the given key in the global registry,
// or nil if there is none.
func LookupAction(typ ActionType, provider, name string) action {
	key := fmt.Sprintf("/%s/%s/%s", typ, provider, name)
	return globalRegistry.lookupAction(key)
}

// listActions returns a list of descriptions of all registered actions.
// The list is sorted by action name.
func (r *registry) listActions() []actionDesc {
	var ads []actionDesc
	r.mu.Lock()
	defer r.mu.Unlock()
	keys := maps.Keys(r.actions)
	slices.Sort(keys)
	for _, key := range keys {
		a := r.actions[key]
		ad := a.desc()
		ad.Key = key
		ads = append(ads, ad)
	}
	return ads
}

// RegisterTraceStore uses the given TraceStore to record traces in the prod environment.
// (A TraceStore that writes to the local filesystem is always installed in the dev environment.)
// The returned function should be called before the program ends to ensure that
// all pending data is stored.
// RegisterTraceStore panics if called more than once.
func RegisterTraceStore(ts TraceStore) (shutdown func(context.Context) error) {
	globalRegistry.registerTraceStore(EnvironmentProd, ts)
	return globalRegistry.tstate.addTraceStoreBatch(ts)
}

func (r *registry) registerTraceStore(env Environment, ts TraceStore) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.traceStores[env]; ok {
		panic(fmt.Sprintf("RegisterTraceStore called twice for environment %q", env))
	}
	r.traceStores[env] = ts
}

func (r *registry) lookupTraceStore(env Environment) TraceStore {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.traceStores[env]
}

// RegisterSpanProcessor registers an OpenTelemetry SpanProcessor for tracing.
func RegisterSpanProcessor(sp sdktrace.SpanProcessor) {
	globalRegistry.registerSpanProcessor(sp)
}

func (r *registry) registerSpanProcessor(sp sdktrace.SpanProcessor) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.tstate.registerSpanProcessor(sp)
}

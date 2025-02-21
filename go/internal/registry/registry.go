// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package registry

import (
	"fmt"
	"log/slog"
	"os"
	"slices"
	"sync"

	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/atype"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"golang.org/x/exp/maps"
)

// This file implements registries of actions and other values.

type Registry struct {
	tstate  *tracing.State
	mu      sync.Mutex
	frozen  bool // when true, no more additions
	actions map[string]action.Action
}

func New() (*Registry, error) {
	r := &Registry{
		actions: map[string]action.Action{},
	}
	r.tstate = tracing.NewState()
	if os.Getenv("GENKIT_TELEMETRY_SERVER") != "" {
		r.tstate.WriteTelemetryImmediate(tracing.NewHTTPTelemetryClient(os.Getenv("GENKIT_TELEMETRY_SERVER")))
	}
	return r, nil
}

func (r *Registry) TracingState() *tracing.State { return r.tstate }

// RegisterAction records the action in the registry.
// It panics if an action with the same type, provider and name is already
// registered.
func (r *Registry) RegisterAction(typ atype.ActionType, a action.Action) {
	key := fmt.Sprintf("/%s/%s", typ, a.Name())
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.frozen {
		panic(fmt.Sprintf("attempt to register action %s in a frozen registry. Register before calling genkit.Init", key))
	}
	if _, ok := r.actions[key]; ok {
		panic(fmt.Sprintf("action %q is already registered", key))
	}
	r.actions[key] = a
	slog.Debug("RegisterAction",
		"type", typ,
		"name", a.Name())
}

func (r *Registry) Freeze() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.frozen = true
}

// LookupAction returns the action for the given key, or nil if there is none.
func (r *Registry) LookupAction(key string) action.Action {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.actions[key]
}

// ListActions returns a list of descriptions of all registered actions.
// The list is sorted by action name.
func (r *Registry) ListActions() []action.Desc {
	var ads []action.Desc
	r.mu.Lock()
	defer r.mu.Unlock()
	keys := maps.Keys(r.actions)
	slices.Sort(keys)
	for _, key := range keys {
		a := r.actions[key]
		ad := a.Desc()
		ad.Key = key
		ads = append(ads, ad)
	}
	return ads
}

func (r *Registry) RegisterSpanProcessor(sp sdktrace.SpanProcessor) {
	r.tstate.RegisterSpanProcessor(sp)
}

// An Environment is the execution context in which the program is running.
type Environment string

const (
	EnvironmentDev  Environment = "dev"  // development: testing, debugging, etc.
	EnvironmentProd Environment = "prod" // production: user data, SLOs, etc.
)

// CurentEnvironment returns the currently active environment.
func CurrentEnvironment() Environment {
	if v := os.Getenv("GENKIT_ENV"); v != "" {
		return Environment(v)
	}
	return EnvironmentProd
}

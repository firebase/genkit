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

package registry

import (
	"crypto/md5"
	"fmt"
	"log"
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"sync"

	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/atype"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"golang.org/x/exp/maps"
)

// This file implements registries of actions and other values.

// The global registry, used in non-test code.
// A test may create their own registries to avoid conflicting with other tests.
var Global *Registry

func init() {
	// Initialize the global registry, along with a dev tracer, at program startup.
	var err error
	Global, err = New()
	if err != nil {
		log.Fatal(err)
	}
}

type Registry struct {
	tstate  *tracing.State
	mu      sync.Mutex
	frozen  bool // when true, no more additions
	actions map[string]action.Action
	flows   []Flow
	// TraceStores, at most one for each [Environment].
	// Only the prod trace store is actually registered; the dev one is
	// always created automatically. But it's simpler if we keep them together here.
	traceStores map[Environment]tracing.Store
}

func New() (*Registry, error) {
	r := &Registry{
		actions:     map[string]action.Action{},
		traceStores: map[Environment]tracing.Store{},
	}
	tstore, err := newDevStore()
	if err != nil {
		return nil, err
	}
	r.RegisterTraceStore(EnvironmentDev, tstore)
	r.tstate = tracing.NewState()
	r.tstate.AddTraceStoreImmediate(tstore)
	return r, nil
}

func (r *Registry) TracingState() *tracing.State { return r.tstate }

func newDevStore() (tracing.Store, error) {
	programName := filepath.Base(os.Args[0])
	rootHash := fmt.Sprintf("%02x", md5.Sum([]byte(programName)))
	dir := filepath.Join(os.TempDir(), ".genkit", rootHash, "traces")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	// Don't remove the temp directory, for post-mortem debugging.
	return tracing.NewFileStore(dir)
}

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
	a.SetTracingState(r.tstate)
	r.actions[key] = a
	slog.Info("RegisterAction",
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

// Flow is the type for the flows stored in a registry.
// Since a registry just remembers flows and returns them,
// this interface is empty.
type Flow interface{}

// RegisterFlow stores the flow for use by the production server (see [NewFlowServeMux]).
// It doesn't check for duplicates because registerAction will do that.
func (r *Registry) RegisterFlow(f Flow) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.flows = append(r.flows, f)
}

func (r *Registry) ListFlows() []Flow {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.flows
}

func (r *Registry) RegisterTraceStore(env Environment, ts tracing.Store) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.traceStores[env]; ok {
		panic(fmt.Sprintf("RegisterTraceStore called twice for environment %q", env))
	}
	r.traceStores[env] = ts
}

func (r *Registry) LookupTraceStore(env Environment) tracing.Store {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.traceStores[env]
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

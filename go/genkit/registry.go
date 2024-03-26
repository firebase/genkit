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
	"log/slog"
	"slices"
	"sync"

	"golang.org/x/exp/maps"
)

// This file implements a global registry of actions and other values.

var (
	registryMu sync.Mutex
	actions    = map[string]action{}
	// TraceStores, at most one for each [Environment].
	// Only the prod trace store is actually registered; the dev one is
	// always created automatically. But it's simpler if we keep them together here.
	traceStores = map[Environment]TraceStore{}
)

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
)

// RegisterAction records the action in the global registry.
// It panics if an action with the same type and ID is already
// registered.
func RegisterAction(typ ActionType, id string, a action) {
	key := fmt.Sprintf("/%s/%s", typ, id)
	registryMu.Lock()
	defer registryMu.Unlock()
	if _, ok := actions[key]; ok {
		panic(fmt.Sprintf("action %q of type %s already has an entry in the registry", id, typ))
	}
	slog.Info("RegisterAction", "key", key)
	actions[key] = a
}

// lookupAction returns the action for the given key, or nil if there is none.
func lookupAction(key string) action {
	registryMu.Lock()
	defer registryMu.Unlock()
	return actions[key]
}

// listActions returns a list of descriptions of all registered actions.
// The list is sorted by action name.
func listActions() []actionDesc {
	var ads []actionDesc
	registryMu.Lock()
	defer registryMu.Unlock()
	keys := maps.Keys(actions)
	slices.Sort(keys)
	for _, key := range keys {
		a := actions[key]
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
	registerTraceStore(EnvironmentProd, ts)
	return initProdTracing(ts)
}

func registerTraceStore(env Environment, ts TraceStore) {
	registryMu.Lock()
	defer registryMu.Unlock()
	if _, ok := traceStores[env]; ok {
		panic(fmt.Sprintf("RegisterTraceStore called twice for environment %q", env))
	}
	traceStores[env] = ts
}

func lookupTraceStore(env Environment) TraceStore {
	registryMu.Lock()
	defer registryMu.Unlock()
	return traceStores[env]
}

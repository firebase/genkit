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
	"fmt"
	"sync"
)

// This file implements a global registry of actions.

var (
	mu      sync.Mutex
	actions = map[string]action{}
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
	mu.Lock()
	defer mu.Unlock()
	if _, ok := actions[key]; ok {
		panic(fmt.Sprintf("action %q of type %s already has an entry in the registry", id, typ))
	}
	actions[key] = a
}

// lookupAction returns the action for the given key, or nil if there is none.
func lookupAction(key string) action {
	mu.Lock()
	defer mu.Unlock()
	return actions[key]
}

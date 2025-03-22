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

package action

import (
	"context"
	"encoding/json"

	"github.com/invopop/jsonschema"
)

// Action is the type that all Action[I, O, S] have in common. Internal version.
type Action interface {
	Name() string

	// RunJSON uses encoding/json to unmarshal the input,
	// calls Action.Run, then returns the marshaled result.
	RunJSON(ctx context.Context, input json.RawMessage, cb func(context.Context, json.RawMessage) error) (json.RawMessage, error)

	// Desc returns a description of the action.
	// It should set all fields of actionDesc except Key, which
	// the registry will set.
	Desc() Desc
}

// A Desc is a description of an Action.
// It is used to provide a list of registered actions.
type Desc struct {
	Key          string             `json:"key"` // full key from the registry
	Name         string             `json:"name"`
	Description  string             `json:"description"`
	Metadata     map[string]any     `json:"metadata"`
	InputSchema  *jsonschema.Schema `json:"inputSchema"`
	OutputSchema *jsonschema.Schema `json:"outputSchema"`
}

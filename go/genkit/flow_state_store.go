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

import "context"

// flowStater is the common type of all flowState[I, O] types.
type flowStater interface {
	isFlowState()
}

// A FlowStateStore stores flow states.
// Every flow state has a unique string identifier.
// A durable FlowStateStore is necessary for durable flows.
type FlowStateStore interface {
	// Save saves the FlowState to the store.
	// TODO(jba): Determine what should happen if the FlowState already exists.
	Save(ctx context.Context, id string, fs flowStater) error
	// Load reads the FlowState with the given ID from the store.
	// It returns an error that is fs.ErrNotExist if there isn't one.
	// pfs must be a pointer to a flowState[I, O] of the correct type.
	Load(ctx context.Context, id string, pfs any) error
}

// nopFlowStateStore is a FlowStateStore that does nothing.
type nopFlowStateStore struct{}

func (nopFlowStateStore) Save(ctx context.Context, id string, fs flowStater) error { return nil }
func (nopFlowStateStore) Load(ctx context.Context, id string, pfs any) error       { return nil }

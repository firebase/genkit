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

// A FlowStateStore stores flow states.
// Every flow state has a unique string identifier.
// A durable FlowStateStore is necessary for durable flows.
type FlowStateStore interface {
	// Save saves the FlowState to the store.
	// TODO(jba): Determine what should happen if the FlowState already exists.
	Save(ctx context.Context, id string, fs *FlowState) error
	// Load reads the FlowState with the given ID from the store.
	// It returns an error that is fs.ErrNotExist if there isn't one.
	Load(ctx context.Context, id string) (*FlowState, error)
	// List returns all the FlowStates in the store that satisfy q, in some deterministic
	// order.
	// It also returns a continuation token: an opaque string that can be passed
	// to the next call to List to resume the listing from where it left off. If
	// the listing reached the end, this is the empty string.
	// If the FlowStateQuery is malformed, List returns an error that is errBadQuery.
	List(ctx context.Context, q *FlowStateQuery) (fss []*FlowState, contToken string, err error)
}

// A FlowStateQuery filters the result of [FlowStateStore.List].
type FlowStateQuery struct {
	// Maximum number of traces to return. If zero, a default value may be used.
	// Callers should not assume they will get the entire list; they should always
	// check the returned continuation token.
	Limit int
	// Where to continue the listing from. Must be either empty to start from the
	// beginning, or the result of a recent, previous call to List.
	ContinuationToken string
}

// nopFlowStateStore is a FlowStateStore that does nothing.
type nopFlowStateStore struct{}

func (nopFlowStateStore) Save(ctx context.Context, id string, fs *FlowState) error { return nil }
func (nopFlowStateStore) Load(ctx context.Context, id string) (*FlowState, error)  { return nil, nil }
func (nopFlowStateStore) List(ctx context.Context, q *FlowStateQuery) (fss []*FlowState, contToken string, err error) {
	return nil, "", nil
}

// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0


package core

import (
	"context"

	"github.com/firebase/genkit/go/internal/base"
)

// A FlowStateStore stores flow states.
// Every flow state has a unique string identifier.
// A durable FlowStateStore is necessary for durable flows.
type FlowStateStore interface {
	// Save saves the FlowState to the store, overwriting an existing one.
	Save(ctx context.Context, id string, fs base.FlowStater) error
	// Load reads the FlowState with the given ID from the store.
	// It returns an error that is fs.ErrNotExist if there isn't one.
	// pfs must be a pointer to a flowState[I, O] of the correct type.
	Load(ctx context.Context, id string, pfs any) error
}

// nopFlowStateStore is a FlowStateStore that does nothing.
type nopFlowStateStore struct{}

func (nopFlowStateStore) Save(ctx context.Context, id string, fs base.FlowStater) error { return nil }
func (nopFlowStateStore) Load(ctx context.Context, id string, pfs any) error            { return nil }

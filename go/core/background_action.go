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

package core

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/internal/registry"
)

// Operation represents a background task operation
type Operation[Out any] struct {
	Action   string         `json:"action,omitempty"`   // The action that created this operation
	ID       string         `json:"id"`                 // Unique identifier for tracking
	Done     bool           `json:"done,omitempty"`     // Whether the operation is complete
	Output   Out            `json:"output,omitempty"`   // Result when done
	Error    error          `json:"error,omitempty"`    // Error if failed
	Metadata map[string]any `json:"metadata,omitempty"` // Additional info
}

// BackgroundModelOptions holds configuration for defining a background model
type BackgroundModelOptions struct {
	Versions       []string       // Known version names for this model
	Supports       any            // Capabilities this model supports
	ConfigSchema   map[string]any // Custom options schema for this model
	Label          string         // Descriptive name for this model
	SupportsCancel bool           // Whether the model supports cancellation
}

// StartOperationFunc starts a background operation
type StartOperationFunc[In, Out any] = func(ctx context.Context, input In) (*Operation[Out], error)

// CheckOperationFunc checks the status of a background operation
type CheckOperationFunc[Out any] = func(ctx context.Context, operation *Operation[Out]) (*Operation[Out], error)

// CancelOperationFunc cancels a background operation
type CancelOperationFunc[Out any] = func(ctx context.Context, operation *Operation[Out]) (*Operation[Out], error)

// BackgroundAction interface represents a background action
type BackgroundAction[In, Out any] interface {
	Start(ctx context.Context, input In) (*Operation[Out], error)
	Check(ctx context.Context, op *Operation[Out]) (*Operation[Out], error)
	Cancel(ctx context.Context, op *Operation[Out]) (*Operation[Out], error)
	SupportsCancel() bool
	Name() string
}

// backgroundActionImpl implements BackgroundAction
type backgroundActionDef[In, Out any] struct {
	startAction    *ActionDef[In, *Operation[Out], struct{}]
	checkAction    *ActionDef[*Operation[Out], *Operation[Out], struct{}]
	cancelAction   *ActionDef[*Operation[Out], *Operation[Out], struct{}]
	name           string
	supportsCancel bool
}

// Start initiates a background operation
func (b *backgroundActionDef[In, Out]) Start(ctx context.Context, input In) (*Operation[Out], error) {
	return b.startAction.Run(ctx, input, nil)
}

// Check polls the status of a background operation
func (b *backgroundActionDef[In, Out]) Check(ctx context.Context, op *Operation[Out]) (*Operation[Out], error) {
	return b.checkAction.Run(ctx, op, nil)
}

// Cancel attempts to cancel a background operation
func (b *backgroundActionDef[In, Out]) Cancel(ctx context.Context, op *Operation[Out]) (*Operation[Out], error) {
	if !b.supportsCancel || b.cancelAction == nil {
		return nil, NewError(UNIMPLEMENTED, "cancel operation not supported")
	}
	return b.cancelAction.Run(ctx, op, nil)
}

// SupportsCancel returns whether the action supports cancellation
func (b *backgroundActionDef[In, Out]) SupportsCancel() bool {
	return b.supportsCancel
}

// Name returns the action name
func (b *backgroundActionDef[In, Out]) Name() string {
	return b.name
}

// DefineBackgroundAction creates and registers a background action with three component actions
func DefineBackgroundAction[In, Out any](
	r *registry.Registry,
	provider, name string,
	config BackgroundModelOptions,
	metadata map[string]any,
	start StartOperationFunc[In, Out],
	check CheckOperationFunc[Out], // Function to check operation status
	cancel CancelOperationFunc[Out], // Optional function to cancel operation
) BackgroundAction[In, Out] {
	// Create the start action - initiates the background operation
	startAction := defineAction(r, provider, name, ActionTypeBackgroundModel, metadata, nil,
		func(ctx context.Context, input In, _ func(context.Context, struct{}) error) (*Operation[Out], error) {
			operation, err := start(ctx, input)
			if err != nil {
				return nil, err
			}
			// Set the action reference in the operation
			operation.Action = fmt.Sprintf("/%s/%s", ActionTypeBackgroundModel, name)
			return operation, nil
		})

	// Create the check action - polls operation status
	checkAction := defineAction(r, provider, name, ActionTypeCheckOperation,
		map[string]any{"description": fmt.Sprintf("Check status of %s operation", name)},
		nil,
		func(ctx context.Context, op *Operation[Out], _ func(context.Context, struct{}) error) (*Operation[Out], error) {
			updatedOp, err := check(ctx, op)
			if err != nil {
				return nil, err
			}
			// Ensure action reference is maintained
			updatedOp.Action = fmt.Sprintf("/%s/%s", ActionTypeCheckOperation, name)
			return updatedOp, nil
		})

	var cancelAction *ActionDef[*Operation[Out], *Operation[Out], struct{}]
	if config.SupportsCancel && cancel != nil {
		// Create the cancel action - cancels operation
		cancelAction = defineAction(r, provider, name, ActionTypeCancelOperation,
			map[string]any{"description": fmt.Sprintf("Cancel %s operation", name)},
			nil,
			func(ctx context.Context, op *Operation[Out], _ func(context.Context, struct{}) error) (*Operation[Out], error) {
				cancelledOp, err := cancel(ctx, op)
				if err != nil {
					return nil, err
				}
				// Ensure action reference is maintained
				cancelledOp.Action = fmt.Sprintf("/%s/%s", ActionTypeCancelOperation, name)
				return cancelledOp, nil
			})
	}

	return &backgroundActionDef[In, Out]{
		startAction:    startAction,
		checkAction:    checkAction,
		cancelAction:   cancelAction,
		name:           name,
		supportsCancel: config.SupportsCancel,
	}
}

// LookupBackgroundAction finds and assembles a background action from the registry
// It corresponds to the TypeScript lookupBackgroundAction function
func LookupBackgroundAction[In, Out any](r *registry.Registry, provider string, name string) BackgroundAction[In, Out] {
	// Look up the root/start action
	startAction := ResolveActionFor[In, *Operation[Out], struct{}](r, ActionTypeBackgroundModel, provider, name)
	if startAction == nil {
		return nil
	}

	// Look up the check action - format: /check-operation/{actionName}/check
	checkAction := ResolveActionFor[*Operation[Out], *Operation[Out], struct{}](r, ActionTypeCheckOperation, provider, name)
	if checkAction == nil {
		return nil
	}
	// Look up the cancel action (optional) - format: /cancel-operation/{actionName}/cancel
	cancelAction := ResolveActionFor[*Operation[Out], *Operation[Out], struct{}](r, ActionTypeCancelOperation, provider, name)

	supportsCancel := cancelAction != nil

	bgAction := backgroundActionDef[In, Out]{
		startAction:    startAction,
		checkAction:    checkAction,
		cancelAction:   cancelAction,
		name:           name,
		supportsCancel: supportsCancel,
	}
	return &bgAction
}

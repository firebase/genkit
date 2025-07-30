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

	"github.com/firebase/genkit/go/internal/registry"
)

// ResourceMatcher provides URI matching capabilities for resources
type ResourceMatcher interface {
	// Matches reports whether this resource matches the given URI
	Matches(uri string) bool
	// ExtractVariables extracts variables from a URI using this resource's template
	ExtractVariables(uri string) (map[string]string, error)
}

// DetachedResourceAction represents a resource that can be temporarily attached to a registry
type DetachedResourceAction interface {
	// Name returns the resource name
	Name() string
	// ResourceMatcher provides URI matching
	ResourceMatcher
	// AttachToRegistry temporarily attaches this resource to a registry.
	// The resource will be automatically cleaned up when the registry is discarded.
	AttachToRegistry(r *registry.Registry)
}

// ResourceExecutor provides resource execution capabilities
type ResourceExecutor interface {
	// Execute runs the resource with the given context and input data
	// Input and output are handled as JSON to avoid package dependencies
	Execute(ctx context.Context, inputJSON []byte) ([]byte, error)
}

// ResourceAction represents a registered resource action
type ResourceAction interface {
	Action
	ResourceMatcher
	ResourceExecutor
}

// ResourceInput represents the input to a resource function.
type ResourceInput struct {
	URI       string            `json:"uri"`       // The resource URI
	Variables map[string]string `json:"variables"` // Extracted variables from URI template matching
}

// ResourceOutput represents the output from a resource function.
// Uses interface{} for Content to avoid package dependencies
type ResourceOutput struct {
	Content []interface{} `json:"content"` // The content parts returned by the resource
}

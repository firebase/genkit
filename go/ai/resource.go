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

package ai

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/firebase/genkit/go/core"
	coreresource "github.com/firebase/genkit/go/core/resource"
	"github.com/firebase/genkit/go/internal/registry"
)

// ResourceInput represents the input to a resource function.
type ResourceInput struct {
	URI       string            `json:"uri"`       // The resource URI
	Variables map[string]string `json:"variables"` // Extracted variables from URI template matching
}

// ResourceOutput represents the output from a resource function.
type ResourceOutput struct {
	Content []*Part `json:"content"` // The content parts returned by the resource
}

// ResourceOptions configures a resource definition.
type ResourceOptions struct {
	URI         string         // Static URI (mutually exclusive with Template)
	Template    string         // URI template (mutually exclusive with URI)
	Description string         // Optional description
	Metadata    map[string]any // Optional metadata
}

// ResourceFunc is a function that loads content for a resource.
type ResourceFunc = func(context.Context, *ResourceInput) (*ResourceOutput, error)

// resource is the internal implementation of the Resource interface.
// It holds the underlying core action and allows looking up resources
// by name without knowing their specific input/output types.
type resource struct {
	core.Action
}

// Resource represents an instance of a resource.
type Resource interface {
	// Name returns the name of the resource.
	Name() string
	// Matches reports whether this resource matches the given URI.
	Matches(uri string) bool
	// ExtractVariables extracts variables from a URI using this resource's template.
	ExtractVariables(uri string) (map[string]string, error)
	// Execute runs the resource with the given input.
	Execute(ctx context.Context, input ResourceInput) (ResourceOutput, error)
	// Register sets the tracing state on the action and registers it with the registry.
	Register(r *registry.Registry)
}

// DefineResource creates a resource and registers it with the given Registry.
func DefineResource(r *registry.Registry, name string, opts *ResourceOptions, fn ResourceFunc) Resource {
	metadata, wrappedFn := implementResource(name, opts, fn)
	resourceAction := core.DefineAction(r, "", name, core.ActionTypeResource, metadata, wrappedFn)
	return &resource{Action: resourceAction}
}

// NewResource creates a resource but does not register it in the registry.
// It can be registered later via the Register method.
func NewResource(name string, opts ResourceOptions, fn ResourceFunc) Resource {
	metadata, wrappedFn := implementResource(name, opts, fn)
	metadata["dynamic"] = true
	resourceAction := core.NewAction("", name, core.ActionTypeResource, metadata, wrappedFn)
	return &resource{Action: resourceAction}
}

// implementResource creates the metadata and wrapped function common to both DefineResource and NewResource.
func implementResource(name string, opts ResourceOptions, fn ResourceFunc) (map[string]any, func(context.Context, ResourceInput) (ResourceOutput, error)) {
	// Validate options - panic like other Define* functions
	if name == "" {
		panic("resource name is required")
	}
	if opts.URI != "" && opts.Template != "" {
		panic("cannot specify both URI and Template")
	}
	if opts.URI == "" && opts.Template == "" {
		panic("must specify either URI or Template")
	}

	// Create metadata with resource-specific information
	metadata := map[string]any{
		"type":        core.ActionTypeResource,
		"name":        name,
		"description": opts.Description,
		"resource": map[string]any{
			"uri":      opts.URI,
			"template": opts.Template,
		},
	}

	// Add user metadata
	if opts.Metadata != nil {
		for k, v := range opts.Metadata {
			metadata[k] = v
		}
	}

	// Wrapped function - just call the user function directly
	wrappedFn := func(ctx context.Context, input ResourceInput) (ResourceOutput, error) {
		return fn(ctx, input)
	}

	return metadata, wrappedFn
}

// Name returns the resource name.
func (r *resource) Name() string {
	return r.Action.Name()
}

// Matches reports whether this resource matches the given URI.
func (r *resource) Matches(uri string) bool {
	desc := r.Action.Desc()
	resourceMeta, ok := desc.Metadata["resource"].(map[string]any)
	if !ok {
		return false
	}

	// Check static URI
	if staticURI, ok := resourceMeta["uri"].(string); ok && staticURI != "" {
		return staticURI == uri
	}

	// Check template
	if template, ok := resourceMeta["template"].(string); ok && template != "" {
		matcher, err := coreresource.NewTemplateMatcher(template)
		if err != nil {
			return false
		}
		return matcher.Matches(uri)
	}

	return false
}

// ExtractVariables extracts variables from a URI using this resource's template.
func (r *resource) ExtractVariables(uri string) (map[string]string, error) {
	desc := r.Action.Desc()
	resourceMeta, ok := desc.Metadata["resource"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("no resource metadata found")
	}

	// Static URI has no variables
	if staticURI, ok := resourceMeta["uri"].(string); ok && staticURI != "" {
		if staticURI == uri {
			return map[string]string{}, nil
		}
		return nil, fmt.Errorf("URI %q does not match static URI %q", uri, staticURI)
	}

	// Extract from template
	if template, ok := resourceMeta["template"].(string); ok && template != "" {
		matcher, err := coreresource.NewTemplateMatcher(template)
		if err != nil {
			return nil, fmt.Errorf("invalid template %q: %w", template, err)
		}
		return matcher.ExtractVariables(uri)
	}

	return nil, fmt.Errorf("no URI or template found in resource metadata")
}

// Execute runs the resource with the given input.
func (r *resource) Execute(ctx context.Context, input ResourceInput) (ResourceOutput, error) {
	// Marshal input to JSON for action call
	inputJSON, err := json.Marshal(input)
	if err != nil {
		return ResourceOutput{}, fmt.Errorf("failed to marshal resource input: %w", err)
	}

	// Use the underlying action to execute the resource function
	outputJSON, err := r.Action.RunJSON(ctx, inputJSON, nil)
	if err != nil {
		return ResourceOutput{}, err
	}

	// Unmarshal output back to ResourceOutput
	var output ResourceOutput
	if err := json.Unmarshal(outputJSON, &output); err != nil {
		return ResourceOutput{}, fmt.Errorf("failed to unmarshal resource output: %w", err)
	}

	return output, nil
}

// Register sets the tracing state on the action and registers it with the registry.
func (r *resource) Register(reg *registry.Registry) {
	r.Action.SetTracingState(reg.TracingState())
	reg.RegisterAction(fmt.Sprintf("/%s/%s", core.ActionTypeResource, r.Action.Name()), r.Action)
}

// FindMatchingResource finds a resource that matches the given URI.
func FindMatchingResource(r *registry.Registry, uri string) (Resource, ResourceInput, error) {
	actions := r.ListActions()

	for _, act := range actions {
		action, ok := act.(core.Action)
		if !ok {
			continue
		}

		desc := action.Desc()
		if desc.Type != core.ActionTypeResource {
			continue
		}

		// Parse resource from Action metadata and use for template resolution
		resource := &resource{Action: action}
		if resource.Matches(uri) {
			variables, err := resource.ExtractVariables(uri)
			if err != nil {
				return nil, ResourceInput{}, err
			}
			return resource, ResourceInput{URI: uri, Variables: variables}, nil
		}
	}

	return nil, ResourceInput{}, fmt.Errorf("no resource found for URI %q", uri)
}

// LookupResource looks up the resource in the registry by provided name and returns it.
func LookupResource(r *registry.Registry, name string) Resource {
	if name == "" {
		return nil
	}

	action := r.LookupAction(fmt.Sprintf("/%s/%s", core.ActionTypeResource, name))
	if action == nil {
		return nil
	}
	return &resource{Action: action.(core.Action)}
}

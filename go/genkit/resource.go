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

package genkit

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/resource"
	"github.com/firebase/genkit/go/internal/registry"
)

// ResourceOutput with concrete ai.Part type for this package
type ResourceOutput struct {
	Content []*ai.Part `json:"content"` // The content parts returned by the resource
}

// ResourceFunc is a function that loads content for a resource.
type ResourceFunc func(context.Context, core.ResourceInput) (ResourceOutput, error)

// ResourceOptions configures a resource definition.
type ResourceOptions struct {
	Name        string         // Required: unique name for the resource
	URI         string         // Static URI (mutually exclusive with Template)
	Template    string         // URI template (mutually exclusive with URI)
	Description string         // Optional description
	Metadata    map[string]any // Optional metadata
}

// resourceAction implements a resource as a core.Action.
type resourceAction struct {
	action  *core.ActionDef[core.ResourceInput, ResourceOutput, struct{}]
	matcher resource.URIMatcher
}

// DefineResource defines a resource and registers it with the Genkit instance.
// Resources provide content that can be referenced in prompts via URI.
//
// Example:
//
//	DefineResource(g, ResourceOptions{
//	  Name: "company-docs",
//	  URI: "file:///docs/handbook.pdf",
//	  Description: "Company handbook",
//	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
//	  content, err := os.ReadFile("/docs/handbook.pdf")
//	  if err != nil {
//	    return ResourceOutput{}, err
//	  }
//	  return ResourceOutput{
//	    Content: []*ai.Part{ai.NewTextPart(string(content))},
//	  }, nil
//	})
func DefineResource(g *Genkit, opts ResourceOptions, fn ResourceFunc) error {
	if opts.Name == "" {
		return fmt.Errorf("resource name is required")
	}

	// Validate URI/Template options
	if opts.URI != "" && opts.Template != "" {
		return fmt.Errorf("cannot specify both URI and Template")
	}
	if opts.URI == "" && opts.Template == "" {
		return fmt.Errorf("must specify either URI or Template")
	}

	// Create matcher
	var matcher resource.URIMatcher

	if opts.URI != "" {
		matcher = resource.NewStaticMatcher(opts.URI)
	} else {
		var err error
		matcher, err = resource.NewTemplateMatcher(opts.Template)
		if err != nil {
			return fmt.Errorf("invalid URI template %q: %w", opts.Template, err)
		}
	}

	// Create metadata with resource-specific information
	metadata := make(map[string]any)
	if opts.Metadata != nil {
		for k, v := range opts.Metadata {
			metadata[k] = v
		}
	}
	metadata["description"] = opts.Description
	metadata["resource"] = map[string]any{
		"uri":      opts.URI,
		"template": opts.Template,
	}

	// Define the action
	action := core.DefineAction(
		g.reg,
		"", // no provider for resources
		opts.Name,
		core.ActionTypeResource,
		metadata,
		fn,
	)

	// Wrap in resourceAction for resource-specific functionality
	resourceAct := &resourceAction{
		action:  action,
		matcher: matcher,
	}

	// Register as a resource (in addition to action registration)
	// This allows resource lookup by URI
	g.reg.RegisterValue(fmt.Sprintf("resource/%s", opts.Name), resourceAct)

	return nil
}

// FindMatchingResource finds a resource that matches the given URI.
func FindMatchingResource(g *Genkit, uri string) (*resourceAction, core.ResourceInput, error) {
	actions := g.reg.ListActions()

	for _, act := range actions {
		action, ok := act.(core.Action)
		if !ok {
			continue
		}

		desc := action.Desc()
		if desc.Type != core.ActionTypeResource {
			continue
		}

		// Look up the resourceAction wrapper
		resourceName := strings.TrimPrefix(desc.Key, "/resource/")
		if resourceAct := g.reg.LookupValue(fmt.Sprintf("resource/%s", resourceName)); resourceAct != nil {
			if ra, ok := resourceAct.(*resourceAction); ok {
				if ra.matcher.Matches(uri) {
					variables, err := ra.matcher.ExtractVariables(uri)
					if err != nil {
						return nil, core.ResourceInput{}, err
					}
					return ra, core.ResourceInput{URI: uri, Variables: variables}, nil
				}
			}
		}
	}

	return nil, core.ResourceInput{}, fmt.Errorf("no resource found for URI %q", uri)
}

// Matches reports whether this resource matches the given URI.
func (r *resourceAction) Matches(uri string) bool {
	return r.matcher.Matches(uri)
}

// Execute runs the resource function with the given input.
func (r *resourceAction) Execute(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
	// Marshal input to JSON for action call
	inputJSON, err := json.Marshal(input)
	if err != nil {
		return ResourceOutput{}, fmt.Errorf("failed to marshal resource input: %w", err)
	}

	output, err := r.action.RunJSON(ctx, inputJSON, nil)
	if err != nil {
		return ResourceOutput{}, err
	}

	// Convert back from JSON to ResourceOutput
	var result ResourceOutput
	if err := json.Unmarshal(output, &result); err != nil {
		return ResourceOutput{}, fmt.Errorf("failed to unmarshal resource output: %w", err)
	}
	return result, nil
}

// ExtractVariables extracts variables from a URI using this resource's template.
func (r *resourceAction) ExtractVariables(uri string) (map[string]string, error) {
	return r.matcher.ExtractVariables(uri)
}

// detachedResourceAction represents a resource action that isn't registered in any registry.
// It can be temporarily attached during generation and implements core.DetachedResourceAction.
type detachedResourceAction struct {
	name        string
	description string
	metadata    map[string]any
	fn          ResourceFunc
	matcher     resource.URIMatcher
}

// DynamicResource creates an unregistered resource action that can be temporarily
// attached during generation via WithResources option.
//
// Example:
//
//	dynamicRes := DynamicResource(ResourceOptions{
//	  Name: "user-data",
//	  Template: "user://profile/{id}",
//	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
//	  userID := input.Variables["id"]
//	  // Load user data dynamically...
//	  return ResourceOutput{Content: []*ai.Part{ai.NewTextPart(userData)}}, nil
//	})
//
//	// Use in generation:
//	ai.Generate(ctx, g,
//	  ai.WithPrompt([]*ai.Part{
//	    ai.NewTextPart("Analyze this user:"),
//	    ai.NewResourcePart("user://profile/123"),
//	  }),
//	  ai.WithResources([]core.DetachedResourceAction{dynamicRes}),
//	)
func DynamicResource(opts ResourceOptions, fn ResourceFunc) (core.DetachedResourceAction, error) {
	if opts.Name == "" {
		return nil, fmt.Errorf("resource name is required")
	}

	// Validate URI/Template options
	if opts.URI != "" && opts.Template != "" {
		return nil, fmt.Errorf("cannot specify both URI and Template")
	}
	if opts.URI == "" && opts.Template == "" {
		return nil, fmt.Errorf("must specify either URI or Template")
	}

	// Create matcher
	var matcher resource.URIMatcher

	if opts.URI != "" {
		matcher = resource.NewStaticMatcher(opts.URI)
	} else {
		var err error
		matcher, err = resource.NewTemplateMatcher(opts.Template)
		if err != nil {
			return nil, fmt.Errorf("invalid URI template %q: %w", opts.Template, err)
		}
	}

	// Create metadata
	metadata := make(map[string]any)
	if opts.Metadata != nil {
		for k, v := range opts.Metadata {
			metadata[k] = v
		}
	}
	metadata["description"] = opts.Description
	metadata["resource"] = map[string]any{
		"uri":      opts.URI,
		"template": opts.Template,
	}
	metadata["dynamic"] = true

	return &detachedResourceAction{
		name:        opts.Name,
		description: opts.Description,
		metadata:    metadata,
		fn:          fn,
		matcher:     matcher,
	}, nil
}

// Name returns the resource name.
func (d *detachedResourceAction) Name() string {
	return d.name
}

// Matches reports whether this resource matches the given URI.
func (d *detachedResourceAction) Matches(uri string) bool {
	return d.matcher.Matches(uri)
}

// Execute runs the resource function with the given input.
func (d *detachedResourceAction) Execute(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
	return d.fn(ctx, input)
}

// ExtractVariables extracts variables from a URI using this resource's template.
// This is primarily for testing purposes.
func (d *detachedResourceAction) ExtractVariables(uri string) (map[string]string, error) {
	return d.matcher.ExtractVariables(uri)
}

// AttachToRegistry temporarily registers this detached resource in the given registry.
// Returns a cleanup function that should be called to remove the resource.
func (d *detachedResourceAction) AttachToRegistry(r *registry.Registry) func() {
	// Create a regular action for this detached resource
	action := core.DefineAction(
		r,
		"", // no provider
		d.name,
		core.ActionTypeResource,
		d.metadata,
		d.fn,
	)

	// Create resource action wrapper
	resourceAct := &resourceAction{
		action:  action,
		matcher: d.matcher,
	}

	// Register as a resource
	resourceKey := fmt.Sprintf("resource/%s", d.name)
	r.RegisterValue(resourceKey, resourceAct)

	// Return cleanup function
	return func() {
	}
}

// Name returns the resource name.
func (r *resourceAction) Name() string {
	return r.action.Name()
}

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
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
)

// DefineResource defines a resource and registers it with the Genkit instance.
// Resources provide content that can be referenced in prompts via URI.
//
// Example:
//
//	DefineResource(g, "company-docs", ai.ResourceOptions{
//	  URI: "file:///docs/handbook.pdf",
//	  Description: "Company handbook",
//	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
//	  content, err := os.ReadFile("/docs/handbook.pdf")
//	  if err != nil {
//	    return ai.ResourceOutput{}, err
//	  }
//	  return ai.ResourceOutput{
//	    Content: []*ai.Part{ai.NewTextPart(string(content))},
//	  }, nil
//	})
func DefineResource(g *Genkit, name string, opts *ai.ResourceOptions, fn ai.ResourceFunc) ai.Resource {
	// Delegate to ai implementation
	return ai.DefineResource(g.reg, resourceName, opts, fn)
}

// FindMatchingResource finds a resource that matches the given URI.
func FindMatchingResource(g *Genkit, uri string) (ai.Resource, ai.ResourceInput, error) {
	return ai.FindMatchingResource(g.reg, uri)
}

// ExecuteResource is a helper to execute an ai.Resource.
func ExecuteResource(ctx context.Context, resource ai.Resource, input ai.ResourceInput) (ai.ResourceOutput, error) {
	return resource.Execute(ctx, input)
}

// NewResource creates an unregistered resource action that can be temporarily
// attached during generation via WithResources option.
//
// Example:
//
//	dynamicRes := NewResource("user-data", ai.ResourceOptions{
//	  Template: "user://profile/{id}",
//	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
//	  userID := input.Variables["id"]
//	  // Load user data dynamically...
//	  return ai.ResourceOutput{Content: []*ai.Part{ai.NewTextPart(userData)}}, nil
//	})
//
//	// Use in generation:
//	ai.Generate(ctx, g,
//	  ai.WithPrompt([]*ai.Part{
//	    ai.NewTextPart("Analyze this user:"),
//	    ai.NewResourcePart("user://profile/123"),
//	  }),
//	  ai.WithResources([]ai.Resource{dynamicRes}),
//	)
func NewResource(resourceName string, opts ai.ResourceOptions, fn ai.ResourceFunc) ai.Resource {
	// Delegate to ai implementation
	return ai.NewResource(resourceName, opts, fn)
}

// ListResources returns a slice of all resource actions
func ListResources(g *Genkit) []ai.Resource {
	acts := g.reg.ListActions()
	resources := []ai.Resource{}
	for _, act := range acts {
		action, ok := act.(core.Action)
		if !ok {
			continue
		}
		actionDesc := action.Desc()
		if actionDesc.Type == core.ActionTypeResource {
			// Look up the resource wrapper
			if resourceValue := g.reg.LookupValue(fmt.Sprintf("resource/%s", actionDesc.Name)); resourceValue != nil {
				if resource, ok := resourceValue.(ai.Resource); ok {
					resources = append(resources, resource)
				}
			}
		}
	}
	return resources
}

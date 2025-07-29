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

package genkit

import (
	"context"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
)

func TestStaticResource(t *testing.T) {
	g, _ := Init(context.Background())

	// Define static resource
	DefineResource(g, ResourceOptions{
		Name: "test-doc",
		URI:  "file:///test.txt",
	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
		return ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("test content")},
		}, nil
	})

	// Find and execute
	resource, input, err := FindMatchingResource(g, "file:///test.txt")
	if err != nil {
		t.Fatalf("resource not found: %v", err)
	}

	output, err := resource.Execute(context.Background(), input)
	if err != nil {
		t.Fatalf("resource execution failed: %v", err)
	}

	if len(output.Content) != 1 || output.Content[0].Text != "test content" {
		t.Fatalf("unexpected output: %v", output.Content)
	}
}

func TestDynamicResourceWithTemplate(t *testing.T) {
	dynResource, err := DynamicResource(ResourceOptions{
		Name:     "user-profile",
		Template: "user://profile/{userID}",
	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
		userID := input.Variables["userID"]
		return ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("User: " + userID)},
		}, nil
	})

	if err != nil {
		t.Fatalf("failed to create dynamic resource: %v", err)
	}

	// Test URI matching
	if !dynResource.Matches("user://profile/123") {
		t.Fatal("should match user://profile/123")
	}

	if dynResource.Matches("user://different/123") {
		t.Fatal("should not match different URI scheme")
	}

	// Test URI matching only - Execute is tested through Generate()
	if !dynResource.Matches("user://profile/alice") {
		t.Fatal("should match user://profile/alice")
	}

	if dynResource.Matches("user://different/alice") {
		t.Fatal("should not match different URI scheme")
	}
}

func TestResourceInGeneration(t *testing.T) {
	g, _ := Init(context.Background())

	// Mock model that echoes input
	DefineModel(g, "", "test", &ai.ModelInfo{
		Supports: &ai.ModelSupports{},
	}, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		var text string
		for _, msg := range req.Messages {
			for _, part := range msg.Content {
				if part.IsText() {
					text += part.Text + " "
				}
			}
		}
		return &ai.ModelResponse{
			Message: &ai.Message{
				Content: []*ai.Part{ai.NewTextPart(text)},
				Role:    "model",
			},
		}, nil
	})

	// Define resource
	DefineResource(g, ResourceOptions{
		Name: "policy",
		URI:  "file:///policy.txt",
	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
		return ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("POLICY_CONTENT")},
		}, nil
	})

	// Generate with resource reference
	resp, err := Generate(context.Background(), g,
		ai.WithModelName("test"),
		ai.WithMessages(ai.NewUserMessage(
			ai.NewTextPart("Read this:"),
			ai.NewResourcePart("file:///policy.txt"),
			ai.NewTextPart("Done."),
		)),
	)

	if err != nil {
		t.Fatalf("generation failed: %v", err)
	}

	// Should contain resolved resource content
	result := resp.Text()
	if !contains(result, "POLICY_CONTENT") {
		t.Fatalf("resource content not found in: %s", result)
	}
}

func TestMissingResourceError(t *testing.T) {
	g, _ := Init(context.Background())

	DefineModel(g, "", "test", &ai.ModelInfo{
		Supports: &ai.ModelSupports{},
	}, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		return &ai.ModelResponse{Message: &ai.Message{Content: []*ai.Part{ai.NewTextPart("ok")}}}, nil
	})

	// Try to use non-existent resource
	_, err := Generate(context.Background(), g,
		ai.WithModelName("test"),
		ai.WithMessages(ai.NewUserMessage(
			ai.NewResourcePart("missing://resource"),
		)),
	)

	if err == nil {
		t.Fatal("expected error for missing resource")
	}

	if !contains(err.Error(), "no resource found") {
		t.Fatalf("wrong error: %v", err)
	}
}

func TestURITemplateMatching(t *testing.T) {
	tests := []struct {
		template string
		uri      string
		match    bool
		vars     map[string]string
	}{
		{"file:///{path}", "file:///data.txt", true, map[string]string{"path": "data.txt"}},
		{"user://profile/{id}", "user://profile/123", true, map[string]string{"id": "123"}},
		{"api://{service}/{version}", "api://users/v1", true, map[string]string{"service": "users", "version": "v1"}},
		{"file:///{path}", "http://wrong", false, nil},
	}

	for _, test := range tests {
		dynResource, err := DynamicResource(ResourceOptions{
			Name:     "test",
			Template: test.template,
		}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
			return ResourceOutput{Content: []*ai.Part{ai.NewTextPart("ok")}}, nil
		})

		if err != nil {
			t.Fatalf("failed to create resource for %s: %v", test.template, err)
		}

		matches := dynResource.Matches(test.uri)
		if matches != test.match {
			t.Fatalf("template %s vs uri %s: expected match=%v, got %v",
				test.template, test.uri, test.match, matches)
		}

		if test.match {
			variables, err := dynResource.ExtractVariables(test.uri)
			if err != nil {
				t.Fatalf("failed to extract variables: %v", err)
			}

			for key, expectedValue := range test.vars {
				if variables[key] != expectedValue {
					t.Fatalf("variable %s: expected %s, got %s", key, expectedValue, variables[key])
				}
			}
		}
	}
}

func contains(s, substr string) bool {
	return strings.Contains(s, substr)
}

func TestDynamicResourceInGeneration(t *testing.T) {
	g, _ := Init(context.Background())

	// Mock model that echoes input
	DefineModel(g, "", "test", &ai.ModelInfo{
		Supports: &ai.ModelSupports{},
	}, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		var text string
		for _, msg := range req.Messages {
			for _, part := range msg.Content {
				if part.IsText() {
					text += part.Text + " "
				}
			}
		}
		return &ai.ModelResponse{
			Message: &ai.Message{
				Content: []*ai.Part{ai.NewTextPart(text)},
				Role:    "model",
			},
		}, nil
	})

	// Create dynamic resource (not registered in registry)
	dynResource, err := DynamicResource(ResourceOptions{
		Name: "dynamic-policy",
		URI:  "dynamic://policy",
	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
		return ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("DYNAMIC_CONTENT")},
		}, nil
	})
	if err != nil {
		t.Fatalf("failed to create dynamic resource: %v", err)
	}

	// Generate with dynamic resource reference using WithResources
	resp, err := Generate(context.Background(), g,
		ai.WithModelName("test"),
		ai.WithMessages(ai.NewUserMessage(
			ai.NewTextPart("Read this:"),
			ai.NewResourcePart("dynamic://policy"),
			ai.NewTextPart("Done."),
		)),
		ai.WithResources([]core.DetachedResourceAction{dynResource}), // 🔑 This is the critical test
	)

	if err != nil {
		t.Fatalf("generation failed: %v", err)
	}

	// Should contain resolved dynamic resource content
	result := resp.Text()
	if !contains(result, "DYNAMIC_CONTENT") {
		t.Fatalf("dynamic resource content not found in: %s", result)
	}
}

func TestMultipleDynamicResourcesInGeneration(t *testing.T) {
	g, _ := Init(context.Background())

	// Mock model that echoes input
	DefineModel(g, "", "test", &ai.ModelInfo{
		Supports: &ai.ModelSupports{},
	}, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		var text string
		for _, msg := range req.Messages {
			for _, part := range msg.Content {
				if part.IsText() {
					text += part.Text + " "
				}
			}
		}
		return &ai.ModelResponse{
			Message: &ai.Message{
				Content: []*ai.Part{ai.NewTextPart(text)},
				Role:    "model",
			},
		}, nil
	})

	// Create multiple dynamic resources
	userResource, err := DynamicResource(ResourceOptions{
		Name:     "user-data",
		Template: "user://profile/{id}",
	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
		userID := input.Variables["id"]
		return ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("USER_" + userID)},
		}, nil
	})
	if err != nil {
		t.Fatalf("failed to create user resource: %v", err)
	}

	projectResource, err := DynamicResource(ResourceOptions{
		Name: "project-data",
		URI:  "project://settings",
	}, func(ctx context.Context, input core.ResourceInput) (ResourceOutput, error) {
		return ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("PROJECT_SETTINGS")},
		}, nil
	})
	if err != nil {
		t.Fatalf("failed to create project resource: %v", err)
	}

	// Generate with multiple dynamic resources
	resp, err := Generate(context.Background(), g,
		ai.WithModelName("test"),
		ai.WithMessages(ai.NewUserMessage(
			ai.NewTextPart("User:"),
			ai.NewResourcePart("user://profile/alice"),
			ai.NewTextPart("Project:"),
			ai.NewResourcePart("project://settings"),
			ai.NewTextPart("Done."),
		)),
		ai.WithResources([]core.DetachedResourceAction{userResource, projectResource}),
	)

	if err != nil {
		t.Fatalf("generation failed: %v", err)
	}

	// Should contain both resolved resources
	result := resp.Text()
	if !contains(result, "USER_alice") {
		t.Fatalf("user resource content not found in: %s", result)
	}
	if !contains(result, "PROJECT_SETTINGS") {
		t.Fatalf("project resource content not found in: %s", result)
	}
}

package genkit

import (
	"context"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

func TestStaticResource(t *testing.T) {
	g, _ := Init(context.Background())

	// Define static resource
	DefineResource(g, "test-doc", ai.ResourceOptions{
		URI: "file:///test.txt",
	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
		return ai.ResourceOutput{
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
	g, _ := Init(context.Background())

	dynResource := NewResource("user-profile", ai.ResourceOptions{
		Template: "user://profile/{userID}",
	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
		userID := input.Variables["userID"]
		return ai.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("User: " + userID)},
		}, nil
	})

	// Register the resource to set up tracing state properly
	dynResource.Register(g.reg)

	// Test URI matching
	if !dynResource.Matches("user://profile/123") {
		t.Fatal("should match user://profile/123")
	}

	if dynResource.Matches("user://different/123") {
		t.Fatal("should not match different URI scheme")
	}

	// Test variable extraction and execution
	variables, err := dynResource.ExtractVariables("user://profile/alice")
	if err != nil {
		t.Fatalf("failed to extract variables: %v", err)
	}

	if variables["userID"] != "alice" {
		t.Fatalf("expected userID=alice, got %s", variables["userID"])
	}

	// Execute with extracted variables
	input := ai.ResourceInput{
		URI:       "user://profile/alice",
		Variables: variables,
	}

	output, err := dynResource.Execute(context.Background(), input)
	if err != nil {
		t.Fatalf("execution failed: %v", err)
	}

	if len(output.Content) != 1 || output.Content[0].Text != "User: alice" {
		t.Fatalf("unexpected output: %v", output.Content)
	}
}

func TestResourceInGeneration(t *testing.T) {
	g, _ := Init(context.Background())

	// Define mock model
	ai.DefineModel(g.reg, "", "test", nil, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		// Extract resource parts from the prompt
		var responseText strings.Builder
		for _, msg := range req.Messages {
			for _, part := range msg.Content {
				if part.Text != "" {
					responseText.WriteString(part.Text + " ")
				}
			}
		}

		return &ai.ModelResponse{
			Request: req,
			Message: &ai.Message{
				Content: []*ai.Part{ai.NewTextPart("Model response: " + responseText.String())},
				Role:    "model",
			},
		}, nil
	})

	// Define resource
	DefineResource(g, "policy", ai.ResourceOptions{
		URI: "file:///policy.txt",
	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
		return ai.ResourceOutput{
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

	if !contains(resp.Text(), "Model response") {
		t.Fatalf("expected model response, got: %s", resp.Text())
	}
}

func TestDynamicResourceInGeneration(t *testing.T) {
	g, _ := Init(context.Background())

	// Define mock model
	ai.DefineModel(g.reg, "", "test", nil, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		var responseText strings.Builder
		for _, msg := range req.Messages {
			for _, part := range msg.Content {
				if part.Text != "" {
					responseText.WriteString(part.Text + " ")
				}
			}
		}

		return &ai.ModelResponse{
			Request: req,
			Message: &ai.Message{
				Content: []*ai.Part{ai.NewTextPart("Model response: " + responseText.String())},
				Role:    "model",
			},
		}, nil
	})

	// Create dynamic resource (not registered in registry)
	dynResource := NewResource("dynamic-policy", ai.ResourceOptions{
		URI: "dynamic://policy",
	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
		return ai.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("DYNAMIC_CONTENT")},
		}, nil
	})

	// Generate with dynamic resource reference using WithResources
	resp, err := Generate(context.Background(), g,
		ai.WithModelName("test"),
		ai.WithMessages(ai.NewUserMessage(
			ai.NewTextPart("Read this:"),
			ai.NewResourcePart("dynamic://policy"),
			ai.NewTextPart("Done."),
		)),
		ai.WithResources([]ai.Resource{dynResource}),
	)

	if err != nil {
		t.Fatalf("generation failed: %v", err)
	}

	if !contains(resp.Text(), "Model response") {
		t.Fatalf("expected model response, got: %s", resp.Text())
	}
}

func TestMultipleDynamicResourcesInGeneration(t *testing.T) {
	g, _ := Init(context.Background())

	// Define mock model
	ai.DefineModel(g.reg, "", "test", nil, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		return &ai.ModelResponse{
			Request: req,
			Message: &ai.Message{
				Content: []*ai.Part{ai.NewTextPart("Model processed all resources")},
				Role:    "model",
			},
		}, nil
	})

	// Create multiple dynamic resources
	userResource := NewResource("user-data", ai.ResourceOptions{
		Template: "user://profile/{id}",
	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
		return ai.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("User: " + input.Variables["id"])},
		}, nil
	})

	projectResource := NewResource("project-data", ai.ResourceOptions{
		URI: "project://settings",
	}, func(ctx context.Context, input ai.ResourceInput) (ai.ResourceOutput, error) {
		return ai.ResourceOutput{
			Content: []*ai.Part{ai.NewTextPart("Project settings")},
		}, nil
	})

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
		ai.WithResources([]ai.Resource{userResource, projectResource}),
	)

	if err != nil {
		t.Fatalf("generation failed: %v", err)
	}

	if !contains(resp.Text(), "Model processed") {
		t.Fatalf("expected model response, got: %s", resp.Text())
	}
}

func contains(s, substr string) bool {
	return strings.Contains(s, substr)
}

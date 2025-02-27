// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googleai

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/firebase/genkit/go/ai"
)

func TestGetContentForCache_NoCacheMetadata(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					{Text: "Hello"},
				},
			},
		},
	}
	gotContent, err := getContentForCache(req, "gemini-1.5-flash-001", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if gotContent != nil {
		t.Errorf("expected nil content when no cache metadata, got: %#v", gotContent)
	}
}

func TestGetContentForCache_NoContentToCache(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Metadata: map[string]interface{}{"cache": map[string]any{
					"ttlSeconds": int(160),
				}},
				// No text content
			},
		},
	}
	_, err := getContentForCache(req, "gemini-1.5-flash-001", nil)
	if err != nil {
		t.Errorf("expected error due to no content to cache, but got nil error")
	}
}

func TestGetContentForCache_Valid(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleSystem,
				Content: []*ai.Part{
					{Text: "System instructions"},
				},
			},
			{
				Role:    ai.RoleUser,
				Content: []*ai.Part{{Text: "Hello user"}},
				Metadata: map[string]interface{}{"cache": map[string]any{
					"ttlSeconds": 160,
				}},
			},
		},
	}
	content, err := getContentForCache(req, "gemini-1.5-flash-001", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if content == nil {
		t.Fatal("expected a non-nil CachedContent")
	}
	/* TODO: enable these checks when upgrading VertexAI Genai SDK
	if content.SystemInstruction == nil {
		t.Error("expected SystemInstruction to be set")
	} else {
		got := ""
		for _, p := range content.SystemInstruction.Parts {
			got += string(p.(genai.Text))
		}
		if !strings.Contains(got, "System instructions") {
			t.Errorf("expected 'System instructions' in system content, got %q", got)
		}
	}*/
	if len(content.Contents) == 0 || content.Contents[0].Role != "user" {
		t.Errorf("expected user content, got %v", content.Contents)
	}
	if content.Model != "gemini-1.5-flash-001" {
		t.Errorf("expected gemini-1.5-flash-001, got %s", content.Model)
	}
}

func TestCalculateTTL(t *testing.T) {
	// if <= 0, we return DEFAULT_TTL
	ttl := calculateTTL(0)
	if ttl != DEFAULT_TTL {
		t.Errorf("expected DEFAULT_TTL %d, got %d", DEFAULT_TTL, ttl)
	}
	ttl = calculateTTL(-10)
	if ttl != DEFAULT_TTL {
		t.Errorf("expected DEFAULT_TTL %d for negative input, got %d", DEFAULT_TTL, ttl)
	}

	// positive
	ttl = calculateTTL(5)
	if ttl != 5*time.Second {
		t.Errorf("expected 5s, got %s", ttl)
	}
}

func TestContains(t *testing.T) {
	slice := []string{"foo", "bar", "baz"}
	if !contains(slice, "foo") {
		t.Errorf("expected slice to contain 'foo'")
	}
	if contains(slice, "notfound") {
		t.Errorf("expected slice NOT to contain 'notfound'")
	}
}

func TestValidateContextCacheRequest_EmptyModelVersion(t *testing.T) {
	req := &ai.ModelRequest{}
	err := validateContextCacheRequest(req, "")
	if err == nil {
		t.Fatal("expected error if modelVersion is empty")
	}
	if !strings.Contains(err.Error(), INVALID_ARGUMENT_MESSAGES.modelVersion) {
		t.Errorf("expected error to contain %q, got %v", INVALID_ARGUMENT_MESSAGES.modelVersion, err)
	}
}

func TestValidateContextCacheRequest_UnknownModelVersion(t *testing.T) {
	req := &ai.ModelRequest{}
	err := validateContextCacheRequest(req, "unknownModel")
	if err == nil {
		t.Fatal("expected error if modelVersion is unknown")
	}
	if !strings.Contains(err.Error(), INVALID_ARGUMENT_MESSAGES.modelVersion) {
		t.Errorf("expected error to contain %q, got %v", INVALID_ARGUMENT_MESSAGES.modelVersion, err)
	}
}

func TestValidateContextCacheRequest_HasTools(t *testing.T) {
	req := &ai.ModelRequest{
		Tools: []*ai.ToolDefinition{{Name: "someTool"}},
	}
	err := validateContextCacheRequest(req, "gemini-1.5-flash-001")
	if err == nil {
		t.Fatal("expected error if Tools are present")
	}
	if !strings.Contains(err.Error(), INVALID_ARGUMENT_MESSAGES.tools) {
		t.Errorf("expected error to contain %q, got %v", INVALID_ARGUMENT_MESSAGES.tools, err)
	}
}

func TestValidateContextCacheRequest_Valid(t *testing.T) {
	req := &ai.ModelRequest{}
	err := validateContextCacheRequest(req, "gemini-1.5-flash-001")
	if err != nil {
		t.Fatalf("did not expect error, got: %v", err)
	}
}

func TestExtractCacheConfig_NoMetadata(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{Role: ai.RoleUser, Content: []*ai.Part{{Text: "Hello"}}},
		},
	}
	endIndex, config, err := extractCacheConfig(req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if endIndex != -1 {
		t.Errorf("expected endOfCachedContents = -1, got %d", endIndex)
	}
	if config != nil {
		t.Errorf("expected nil cacheConfig, got %#v", config)
	}
}

func TestExtractCacheConfig_MapTTL(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					{Text: "Hello"},
				},
				Metadata: map[string]interface{}{
					"cache": map[string]interface{}{
						"ttlSeconds": int(123),
					},
				},
			},
		},
	}
	endIndex, config, err := extractCacheConfig(req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if endIndex != 0 {
		t.Errorf("expected endIndex=0, got %d", endIndex)
	}
	if config == nil {
		t.Fatal("expected non-nil config")
	}
	if config.TTL != 123 {
		t.Errorf("expected TTLSeconds=123, got %v", config.TTL)
	}
}

func TestExtractCacheConfig_InvalidCacheType(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					{Text: "Hello"},
				},
				Metadata: map[string]interface{}{
					"cache": []string{"not valid"},
				},
			},
		},
	}
	endIndex, config, err := extractCacheConfig(req)
	if err == nil {
		t.Fatal("expected error for invalid cache type")
	}
	if endIndex != -1 {
		t.Errorf("expected endIndex=-1, got %d", endIndex)
	}
	if config != nil {
		t.Errorf("expected config to be nil, got %#v", config)
	}
}

func TestHandleCacheIfNeeded_NoCacheConfig(t *testing.T) {
	req := &ai.ModelRequest{}
	content, err := handleCacheIfNeeded(context.Background(), state.gclient, req, "gemini-1.5-flash-001", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if content != nil {
		t.Errorf("expected nil content if no cache config, got: %#v", content)
	}
}

func TestHandleCacheIfNeeded_Tools(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					{Text: "Hello"},
				},
				Metadata: map[string]interface{}{
					"cache": map[string]interface{}{
						"ttlSeconds": int(123),
					},
				},
			},
		},

		Tools: []*ai.ToolDefinition{{Name: "someTool"}},
	}
	cc := &CacheConfigDetails{}
	content, err := handleCacheIfNeeded(context.Background(), state.gclient, req, "gemini-1.5-flash-001", cc)
	if err == nil {
		t.Fatalf("tool use is not allowed when caching contents")
	}
	if content != nil {
		t.Errorf("expected nil content if request invalid, got: %#v", content)
	}
}

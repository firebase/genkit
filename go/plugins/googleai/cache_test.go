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
	gotContent, err := getContentForCache(req, "gemini-1.5-flash-001")
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
	_, err := getContentForCache(req, "gemini-1.5-flash-001")
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
	content, err := getContentForCache(req, "gemini-1.5-flash-001")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if content == nil {
		t.Fatal("expected a non-nil CachedContent")
	}
	if len(content.Contents) == 0 || content.Contents[0].Role != "user" {
		t.Errorf("expected user content, got %v", content.Contents)
	}
	if content.Model != "gemini-1.5-flash-001" {
		t.Errorf("expected gemini-1.5-flash-001, got %s", content.Model)
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
	endIndex, ttl, err := findCacheMarker(req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if endIndex != -1 {
		t.Errorf("expected end of cache index = -1, got %d", endIndex)
	}
	if ttl != 0 {
		t.Errorf("expected cache ttlSeconds = 0, got %d", ttl)
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
	endIndex, ttl, err := findCacheMarker(req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if endIndex != 0 {
		t.Errorf("expected endIndex=0, got %d", endIndex)
	}
	if ttl != time.Duration(123)*time.Second {
		t.Errorf("expected TTLSeconds=123, got %v", ttl)
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
	endIndex, ttl, err := findCacheMarker(req)
	if err == nil {
		t.Fatal("expected error for invalid cache type")
	}
	if endIndex != -1 {
		t.Errorf("expected endIndex=-1, got %d", endIndex)
	}
	if ttl != 0 {
		t.Errorf("expected cache ttlSeconds = 0, got %d", ttl)
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
	content, err := handleCacheIfNeeded(context.Background(), state.gclient, req, "gemini-1.5-flash-001")
	if err == nil {
		t.Fatalf("tool use is not allowed when caching contents")
	}
	if content != nil {
		t.Errorf("expected nil content if request invalid, got: %#v", content)
	}
}

func TestHandleCacheIfNeeded_SystemPrompt_and_Tools(t *testing.T) {
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
			{
				Role: ai.RoleSystem,
				Content: []*ai.Part{
					{Text: "talk like a pirate"},
				},
			},
		},
		Tools: []*ai.ToolDefinition{{Name: "someTool"}},
	}
	content, err := handleCacheIfNeeded(context.Background(), state.gclient, req, "gemini-1.5-flash-001")
	if err == nil {
		t.Fatalf("system prompt use is not allowed when caching contents")
	}
	if content != nil {
		t.Errorf("expected nil content if request invalid, got: %#v", content)
	}
}

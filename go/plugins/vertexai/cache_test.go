// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai

import (
	"context"
	"crypto/sha256"
	"fmt"
	"strings"
	"testing"
	"time"

	"cloud.google.com/go/vertexai/genai"
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
	gotContent, err := getContentForCache(req, "gemini-1.5-flash", nil)
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
				Role:     ai.RoleUser,
				Metadata: map[string]interface{}{"cache": true},
				// No text content
			},
		},
	}
	_, err := getContentForCache(req, "gemini-1.5-flash", nil)
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
				Role:     ai.RoleUser,
				Content:  []*ai.Part{{Text: "Hello user"}},
				Metadata: map[string]interface{}{"cache": true},
			},
		},
	}
	content, err := getContentForCache(req, "gemini-1.5-flash", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if content == nil {
		t.Fatal("expected a non-nil CachedContent")
	}
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
	}
	if len(content.Contents) == 0 || content.Contents[0].Role != "user" {
		t.Errorf("expected user content, got %v", content.Contents)
	}
	if content.Model != "gemini-1.5-flash" {
		t.Errorf("expected gemini-1.5-flash, got %s", content.Model)
	}
}

func TestGenerateCacheKey(t *testing.T) {
	content := &genai.CachedContent{
		Model: "gemini-1.5-flash",
		SystemInstruction: &genai.Content{
			Role:  "system",
			Parts: []genai.Part{genai.Text("System message")},
		},
		Contents: []*genai.Content{
			{
				Role:  "user",
				Parts: []genai.Part{genai.Text("User message")},
			},
		},
	}
	key := generateCacheKey(content)
	if len(key) == 0 {
		t.Fatal("expected non-empty key")
	}
	// It's a SHA256 sum, so length in hex is 64
	if len(key) != 64 {
		t.Errorf("expected 64 hex chars, got %d: %s", len(key), key)
	}

	// Quick sanity check by hashing ourselves:
	h := sha256.New()
	h.Write([]byte("System message"))
	h.Write([]byte("gemini-1.5-flash"))
	h.Write([]byte("User message"))
	exp := fmt.Sprintf("%x", h.Sum(nil))
	if key != exp {
		t.Errorf("hash mismatch: expected %s, got %s", exp, key)
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

func TestGetKeysFrom(t *testing.T) {
	m := map[string]ai.ModelCapabilities{
		"alpha": {},
		"beta":  {},
	}
	keys := getKeysFrom(m)
	if len(keys) != 2 {
		t.Errorf("expected 2 keys, got %d", len(keys))
	}
	foundAlpha := false
	foundBeta := false
	for _, k := range keys {
		if k == "alpha" {
			foundAlpha = true
		}
		if k == "beta" {
			foundBeta = true
		}
	}
	if !foundAlpha || !foundBeta {
		t.Errorf("expected 'alpha' and 'beta' in keys, got %v", keys)
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
	err := validateContextCacheRequest(req, "gemini-1.5-flash")
	if err == nil {
		t.Fatal("expected error if Tools are present")
	}
	if !strings.Contains(err.Error(), INVALID_ARGUMENT_MESSAGES.tools) {
		t.Errorf("expected error to contain %q, got %v", INVALID_ARGUMENT_MESSAGES.tools, err)
	}
}

func TestValidateContextCacheRequest_Valid(t *testing.T) {
	req := &ai.ModelRequest{}
	err := validateContextCacheRequest(req, "gemini-1.5-flash")
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

func TestExtractCacheConfig_BooleanTrue(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role:     ai.RoleUser,
				Content:  []*ai.Part{{Text: "Hello"}},
				Metadata: map[string]interface{}{"cache": true},
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
	if config.TTL != 0 {
		t.Errorf("expected TTLSeconds = 0, got %v", config.TTL)
	}
}

func TestExtractCacheConfig_BooleanFalse(t *testing.T) {
	req := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role:     ai.RoleUser,
				Content:  []*ai.Part{{Text: "Hello"}},
				Metadata: map[string]interface{}{"cache": false},
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
	if config.TTL != 0 {
		t.Errorf("expected TTLSeconds=0, got %v", config.TTL)
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
						"ttlSeconds": float64(123),
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
	if !strings.Contains(err.Error(), "invalid cache config type") {
		t.Errorf("unexpected error text: %v", err)
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
	content, err := handleCacheIfNeeded(context.Background(), state.gclient, req, "gemini-1.5-flash", nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if content != nil {
		t.Errorf("expected nil content if no cache config, got: %#v", content)
	}
}

func TestHandleCacheIfNeeded_RequestInvalid(t *testing.T) {
	req := &ai.ModelRequest{
		Tools: []*ai.ToolDefinition{{Name: "someTool"}},
	}
	cc := &CacheConfigDetails{}
	content, err := handleCacheIfNeeded(context.Background(), state.gclient, req, "gemini-1.5-flash", cc)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if content != nil {
		t.Errorf("expected nil content if request invalid, got: %#v", content)
	}
}

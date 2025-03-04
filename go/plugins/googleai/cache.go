// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googleai

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"slices"
	"strings"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/iterator"
)

// DEFAULT_TTL in seconds (5 minutes)
const DEFAULT_TTL = 300

var ContextCacheSupportedModels = [...]string{
	"gemini-2.0-flash-lite-001",
	"gemini-2.0-flash-001",

	"gemini-1.5-flash-001",
	"gemini-1.5-flash-002",

	"gemini-1.5-pro-001",
	"gemini-1.5-pro-002",
}

var INVALID_ARGUMENT_MESSAGES = struct {
	modelVersion string
	tools        string
	systemPrompt string
}{
	modelVersion: fmt.Sprintf(
		"unsupported model version, expected: %s",
		strings.Join(ContextCacheSupportedModels[:], ", ")),
	tools:        "tools are not supported with context caching",
	systemPrompt: "system prompts are not supported with context caching",
}

// getContentForCache inspects the request and modelVersion, and constructs a
// genai.CachedContent that should be cached.
// This is where you decide what goes into the cache: large documents, system instructions, etc.
func getContentForCache(
	request *ai.ModelRequest,
	modelVersion string,
) (*genai.CachedContent, error) {
	cacheEndIdx, ttl, err := findCacheMarker(request)
	if err != nil {
		return nil, err
	}
	// no cache message found
	if cacheEndIdx == -1 {
		return nil, err
	}

	if cacheEndIdx < 0 || cacheEndIdx >= len(request.Messages) {
		return nil, fmt.Errorf("end of cached contents, index %d is invalid", cacheEndIdx)
	}

	var messagesForCache []*genai.Content
	for i := cacheEndIdx; i >= 0; i-- {
		if request.Messages[i].Role == ai.RoleSystem {
			continue
		}
		parts, err := convertParts(request.Messages[i].Content)
		if err != nil {
			return nil, err
		}
		messagesForCache = append(messagesForCache, &genai.Content{
			Role:  string(request.Messages[i].Role),
			Parts: parts,
		})
	}

	return &genai.CachedContent{
		Model:      modelVersion,
		Contents:   messagesForCache,
		Expiration: genai.ExpireTimeOrTTL{TTL: ttl},
	}, nil
}

// validateContextCacheRequest checks for supported models and checks if Tools
// are being provided in the request
func validateContextCacheRequest(request *ai.ModelRequest, modelVersion string) error {
	if modelVersion == "" || !slices.Contains(ContextCacheSupportedModels[:], modelVersion) {
		return fmt.Errorf("%s", INVALID_ARGUMENT_MESSAGES.modelVersion)
	}
	if len(request.Tools) > 0 {
		return fmt.Errorf("%s", INVALID_ARGUMENT_MESSAGES.tools)
	}
	for _, m := range request.Messages {
		if m.Role == ai.RoleSystem {
			return fmt.Errorf("%s", INVALID_ARGUMENT_MESSAGES.systemPrompt)
		}
	}

	return nil
}

// findCacheMarker finds the cache mark in the list of request messages.
// All of the messages preceding this mark will be cached
func findCacheMarker(request *ai.ModelRequest) (cacheEndIdx int, ttl time.Duration, err error) {
	for i := len(request.Messages) - 1; i >= 0; i-- {
		m := request.Messages[i]
		if m.Metadata == nil {
			continue
		}

		cacheVal, exists := m.Metadata["cache"]
		if !exists || cacheVal == nil {
			continue
		}

		c, ok := cacheVal.(map[string]any)
		if !ok {
			return -1, 0, fmt.Errorf("cache metadata should be map but got: %T", cacheVal)
		}

		if t, ok := c["ttlSeconds"].(int); ok {
			fmt.Printf("found ttlSeconds: %d\n\n", t)
			return i, time.Duration(t) * time.Second, nil
		}

		return -1, 0, fmt.Errorf("invalid type for cache ttlSeconds, expected int, got %T", c["ttlSeconds"])
	}
	return -1, 0, nil
}

// lookupCache retrieves a *genai.CachedContent from a given cache key
func lookupCache(ctx context.Context, client *genai.Client, key string) (*genai.CachedContent, error) {
	if key == "" {
		return nil, fmt.Errorf("empty cache key detected")
	}

	it := client.ListCachedContents(ctx)
	for {
		cc, err := it.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil, err
		}
		if key == cc.DisplayName {
			return cc, nil
		}
	}

	return nil, nil
}

// genCacheKey generates a sha256 key for cached content used to
// create or lookup caches during generate requests
func genCacheKey(content *genai.CachedContent) string {
	hash := sha256.New()

	// Incorporate content parts to ensure uniqueness
	for _, c := range content.Contents {
		for _, p := range c.Parts {
			switch v := p.(type) {
			case genai.Text:
				hash.Write([]byte(v))
			case genai.Blob:
				hash.Write([]byte(v.MIMEType))
				hash.Write(v.Data)
			}
		}
	}
	return hex.EncodeToString(hash.Sum(nil))
}

// handleCacheIfNeeded checks if caching should be used, attempts to find or create the cache,
// and returns the cached content if applicable.
func handleCacheIfNeeded(
	ctx context.Context,
	client *genai.Client,
	request *ai.ModelRequest,
	modelVersion string,
) (*genai.CachedContent, error) {
	// since context caching is only available for specific model versions, we
	// must make sure the configuration has the right version
	if c, ok := request.Config.(*ai.GenerationCommonConfig); ok {
		modelVersion = c.Version
	}
	err := validateContextCacheRequest(request, modelVersion)
	if err != nil {
		return nil, err
	}

	// obtain message parts to be cached
	cc, err := getContentForCache(request, modelVersion)
	if err != nil {
		return nil, err
	}

	// generate cache key and check if cache already exists before creating one
	key := genCacheKey(cc)
	newCache, err := lookupCache(ctx, client, key)
	if err != nil {
		return nil, err
	}
	if newCache != nil {
		return client.GetCachedContent(ctx, newCache.Name)
	}

	cc.DisplayName = key
	newCache, err = client.CreateCachedContent(ctx, cc)

	return newCache, nil
}

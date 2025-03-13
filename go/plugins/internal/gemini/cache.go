// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0
//

package gemini

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"google.golang.org/genai"
)

const CacheContentsPerPage = 5

var cacheSupportedVersions = []string{
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
		strings.Join(cacheSupportedVersions[:], ", ")),
	tools:        "tools are not supported with context caching",
	systemPrompt: "system prompts are not supported with context caching",
}

// HandleCache checks if caching should be used, attempts to find or create the cache,
// and returns the cached content if applicable.
func handleCache(
	ctx context.Context,
	client *genai.Client,
	request *ai.ModelRequest,
	model string,
) (*genai.CachedContent, error) {
	cc, err := prepareCacheContent(request, model)
	if err != nil {
		return nil, err
	}
	if cc == nil {
		return nil, nil
	}

	cache, err := lookupCache(ctx, client, cc.DisplayName)
	if err != nil {
		return nil, err
	}
	if cache == nil {
		return client.Caches.Create(ctx, model, cc)
	}

	return cache, nil
}

// prepareCacheContent inspects the request and modelVersion, and constructs a
// genai.CachedContent that should be cached.
// This is where you decide what goes into the cache: large documents, system instructions, etc.
func prepareCacheContent(
	request *ai.ModelRequest,
	model string,
) (*genai.CreateCachedContentConfig, error) {
	cacheEndIdx, ttl, err := findCacheMarker(request)
	if err != nil {
		return nil, err
	}
	// no cache mark found
	if cacheEndIdx == -1 {
		return nil, err
	}
	// index out of bounds
	if cacheEndIdx < 0 || cacheEndIdx >= len(request.Messages) {
		return nil, fmt.Errorf("end of cached contents, index %d is invalid", cacheEndIdx)
	}

	// since context caching is only available for specific model versions, we
	// must make sure the configuration has the right version
	err = validateContextCacheRequest(request, model)
	if err != nil {
		return nil, err
	}

	var messagesToCache []*genai.Content
	for i := cacheEndIdx; i >= 0; i-- {
		m := request.Messages[i]
		if m.Role == ai.RoleSystem {
			continue
		}
		parts, err := convertParts(m.Content)
		if err != nil {
			return nil, err
		}
		messagesToCache = append(messagesToCache, &genai.Content{
			Parts: parts,
			Role:  string(m.Role),
		})
	}

	key := calculateCacheKey(messagesToCache)

	return &genai.CreateCachedContentConfig{
		DisplayName: key,
		TTL:         strconv.Itoa(ttl) + "s",
		Contents:    messagesToCache,
	}, nil
}

// validateContextCacheRequest checks for supported models and checks if Tools
// are being provided in the request
func validateContextCacheRequest(request *ai.ModelRequest, modelVersion string) error {
	if modelVersion == "" || !slices.Contains(cacheSupportedVersions, modelVersion) {
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
func findCacheMarker(request *ai.ModelRequest) (cacheEndIdx int, ttl int, err error) {
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
			return i, t, nil
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

	var nextPageToken string
	for {
		page, err := client.Caches.List(ctx, &genai.ListCachedContentsConfig{
			PageSize:  CacheContentsPerPage,
			PageToken: nextPageToken,
		})
		if err != nil && err != genai.ErrPageDone {
			return nil, err
		}
		// check page contents to see if cache is found
		for _, cache := range page.Items {
			if cache.DisplayName == key {
				return cache, nil
			}
		}
		// no cache found in the list, it might not be created yet
		if err == genai.ErrPageDone {
			return nil, nil
		}

		nextPageToken = page.NextPageToken
		if nextPageToken == "" {
			break
		}
	}

	return nil, nil
}

// calculateCacheKey generates a sha256 key for cached content used to
// create or lookup caches during generate requests
func calculateCacheKey(content []*genai.Content) string {
	hash := sha256.New()

	// Incorporate content parts to ensure uniqueness
	for _, c := range content {
		for _, p := range c.Parts {
			if p.Text != "" {
				hash.Write([]byte(p.Text))
			} else if p.InlineData != nil {
				hash.Write([]byte(p.InlineData.MIMEType))
				hash.Write([]byte(p.InlineData.Data))
			}
		}
	}
	return hex.EncodeToString(hash.Sum(nil))
}

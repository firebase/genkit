// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai

import (
	"context"
	"fmt"
	"strings"
	"time"

	"cloud.google.com/go/vertexai/genai"
	"github.com/firebase/genkit/go/ai"
)

// DEFAULT_TTL in seconds (5 minutes)
const DEFAULT_TTL = 300

// CacheConfigDetails holds configuration details for caching.
// Adjust fields as needed for your use case.
type CacheConfigDetails struct {
	// TTL in seconds is how long to keep the cached content.
	// If zero, defaults to 60 minutes.
	TTL time.Duration
}

var ContextCacheSupportedModels = [...]string{
	"gemini-1.5-flash-001",
	"gemini-1.5-pro-001",
}

var INVALID_ARGUMENT_MESSAGES = struct {
	modelVersion string
	tools        string
}{
	modelVersion: fmt.Sprintf(
		"unsupported model version, expected: %s",
		strings.Join(ContextCacheSupportedModels[:], ", ")),
	tools: "tools are not supported with context caching",
	// TODO: add system prompt constraint to avoid grpc error
}

// getContentForCache inspects the request and modelVersion, and constructs a
// genai.CachedContent that should be cached.
// This is where you decide what goes into the cache: large documents, system instructions, etc.
func getContentForCache(
	request *ai.ModelRequest,
	modelVersion string,
	cacheConfig *CacheConfigDetails,
) (*genai.CachedContent, error) {
	endOfCachedContents, extractedCacheConfig, err := extractCacheConfig(request)
	if err != nil {
		return nil, err
	}

	// If no cache metadata found, return nil
	if extractedCacheConfig == nil {
		return nil, nil
	}
	if endOfCachedContents < 0 || endOfCachedContents >= len(request.Messages) {
		return nil, fmt.Errorf("invalid endOfCachedContents index")
	}
	if cacheConfig == nil {
		cacheConfig = extractedCacheConfig
	}

	var messagesForCache []*genai.Content
	for i := endOfCachedContents; i >= 0; i-- {
		// system instructions should not be used for cache
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
		Expiration: genai.ExpireTimeOrTTL{TTL: calculateTTL(cacheConfig.TTL)},
	}, nil
}

// calculateTTL returns the TTL as a time.Duration.
func calculateTTL(ttl time.Duration) time.Duration {
	if ttl <= 0 {
		return DEFAULT_TTL
	}
	return ttl * time.Second
}

// contains checks if a slice contains a given string.
func contains(slice []string, target string) bool {
	for _, s := range slice {
		if s == target {
			return true
		}
	}
	return false
}

// validateContextCacheRequest checks for supported models and checks if Tools
// are being provided in the request
func validateContextCacheRequest(request *ai.ModelRequest, modelVersion string) error {
	if modelVersion == "" || !contains(ContextCacheSupportedModels[:], modelVersion) {
		return fmt.Errorf("%s", INVALID_ARGUMENT_MESSAGES.modelVersion)
	}
	if len(request.Tools) > 0 {
		return fmt.Errorf("%s", INVALID_ARGUMENT_MESSAGES.tools)
	}

	// If we reach here, request is valid for context caching
	return nil
}

func extractCacheConfig(request *ai.ModelRequest) (int, *CacheConfigDetails, error) {
	endOfCachedContents := -1
	var cacheConfig *CacheConfigDetails

	// find the cache mark in the list of request messages
	for i := len(request.Messages) - 1; i >= 0; i-- {
		m := request.Messages[i]
		if m.Metadata == nil {
			continue
		}

		// found the cache key and its content is a map
		if c, ok := m.Metadata["cache"].(map[string]any); ok && c != nil {
			// Found a message with `metadata.cache`
			endOfCachedContents = i

			// only accepting ints for ttlSeconds
			if ttlVal, ok := c["ttlSeconds"].(int); ok {
				cacheConfig = &CacheConfigDetails{
					TTL: time.Duration(ttlVal),
				}
			} else {
				return -1, nil, fmt.Errorf("invalid type for cache ttlSeconds, expected int, got %T", ttlVal)
			}
			break
		} else {
			return -1, nil, fmt.Errorf("cache metadata should be a map but got %T", m.Metadata["cache"])
		}
	}

	if endOfCachedContents == -1 {
		// No cache metadata found
		return -1, nil, nil
	}

	return endOfCachedContents, cacheConfig, nil
}

// handleCacheIfNeeded checks if caching should be used, attempts to find or create the cache,
// and returns the cached content if applicable.
func handleCacheIfNeeded(
	ctx context.Context,
	client *genai.Client,
	request *ai.ModelRequest,
	modelVersion string,
	cacheConfig *CacheConfigDetails,
) (*genai.CachedContent, error) {
	if cacheConfig == nil {
		return nil, nil
	}

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
	cc, err := getContentForCache(request, modelVersion, cacheConfig)
	if err != nil {
		return nil, err
	}

	// cc.Model = modelVersion
	return client.CreateCachedContent(ctx, cc)
}

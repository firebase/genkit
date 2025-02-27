// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
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
}

// validateHistoryLength validates that the request and chat session history
// lengths align
func validateHistoryLength(request *ai.ModelRequest, cs *genai.ChatSession) error {
	systemMessages := 0

	// in Gemini, system messages are not part of the chat history
	for _, m := range request.Messages {
		if m.Role == ai.RoleSystem {
			systemMessages += 1
		}
	}

	if len(cs.History) != len(request.Messages)-systemMessages-1 {
		return fmt.Errorf("history length mismatch, chat session: %d, request messages: %d", len(cs.History), len(request.Messages)-1)
	}

	return nil
}

type contentForCache struct {
	cacheConfig *CacheConfigDetails
	content     *genai.CachedContent
}

// getContentForCache inspects the request and modelVersion, and constructs a
// genai.CachedContent that should be cached.
// This is where you decide what goes into the cache: large documents, system instructions, etc.
func getContentForCache(
	request *ai.ModelRequest,
	modelVersion string,
	cacheConfig *CacheConfigDetails,
	cs *genai.ChatSession,
) (*contentForCache, error) {
	err := validateHistoryLength(request, cs)
	if err != nil {
		return nil, err
	}

	endOfCachedContents, extractedCacheConfig, err := extractCacheConfig(request)
	if err != nil {
		return nil, err
	}

	fmt.Printf("cacheConfig: %#v\n\n", cacheConfig)
	fmt.Printf("endOfCachedContents: %v\n\n", endOfCachedContents)
	fmt.Printf("extractedCacheConfig: %#v\n\n", extractedCacheConfig)

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
			fmt.Printf("oop, found a system role: %#v\n\n", request.Messages[i].Role)
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

	content := &genai.CachedContent{
		Model:      modelVersion,
		Contents:   messagesForCache,
		Expiration: genai.ExpireTimeOrTTL{TTL: calculateTTL(cacheConfig.TTL)},
	}

	return &contentForCache{
		cacheConfig: cacheConfig,
		content:     content,
	}, nil
}

// generateCacheKey creates a unique key for the cached content based on its contents.
// We can hash the system instruction and model version.
func generateCacheKey(content *genai.CachedContent) string {
	hash := sha256.New()
	if content.SystemInstruction != nil {
		for _, p := range content.SystemInstruction.Parts {
			if t, ok := p.(genai.Text); ok {
				hash.Write([]byte(t))
			}
		}
	}
	hash.Write([]byte(content.Model))

	// Also incorporate any user content parts to ensure uniqueness
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
		fmt.Printf("m contents: %#v\n\n", m)
		if m.Metadata == nil {
			continue
		}

		// found the cache key and its content is a map
		fmt.Printf("m.Metadata[cache]: %#v\n\n", m.Metadata["cache"])
		if c, ok := m.Metadata["cache"].(map[string]any); ok && c != nil {
			fmt.Printf("[%d] FOUND METADATA! %#v\n\n", i, m.Metadata["cache"])
			// Found a message with `metadata.cache`
			endOfCachedContents = i

			ttl := time.Duration(0)
			if ttlVal, ok := c["ttlSeconds"].(int); ok {
				ttl = time.Duration(ttlVal)
			}
			cacheConfig = &CacheConfigDetails{
				TTL: ttl,
			}
			break
		}
	}

	if endOfCachedContents == -1 {
		// No cache metadata found
		return -1, nil, nil
	}

	fmt.Printf("cacheConfig: %#v\n\n")
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
	cs *genai.ChatSession,
) (*contentForCache, error) {
	if cacheConfig == nil {
		return nil, nil
	}

	if c, ok := request.Config.(*ai.GenerationCommonConfig); ok {
		modelVersion = c.Version
	}

	// since context caching is only available for specific model versions, we
	// must make sure the configuration has the right version
	err := validateContextCacheRequest(request, modelVersion)
	if err != nil {
		return nil, err
	}

	cc, err := getContentForCache(request, modelVersion, cacheConfig, cs)
	if err != nil {
		return nil, err
	}

	cc.content.Model = modelVersion
	fmt.Printf("generating cache key for model: %s - %#v\n\n", cc.content.Model, cc.content)
	// cacheKey := generateCacheKey(cc.content)
	// fmt.Printf("cache key: %s\n\n", cacheKey)

	newCache, err := client.CreateCachedContent(ctx, cc.content)
	if err != nil {
		fmt.Errorf("OOPS: %#v", err)
		if strings.Contains(err.Error(), "The minimum token count to start caching is") {
			return nil, err
		}
		return nil, fmt.Errorf("failed to create cache: %v", err)
	}

	cc.content = newCache
	fmt.Printf("generated cache: %#v\n\n", newCache)
	return cc, nil
}

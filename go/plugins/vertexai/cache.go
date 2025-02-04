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

package vertexai

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"log/slog"
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

var (
	INVALID_ARGUMENT_MESSAGES = struct {
		modelVersion string
		tools        string
	}{
		modelVersion: "Invalid modelVersion specified.",
		tools:        "Tools are not supported with context caching.",
	}
)

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
	var systemInstruction string
	var userParts []*genai.Content

	for _, m := range request.Messages {
		if m.Role == ai.RoleSystem {
			sysParts := []string{}
			for _, p := range m.Content {
				if p.IsText() {
					sysParts = append(sysParts, p.Text)
				}
			}
			if len(sysParts) > 0 {
				systemInstruction = strings.Join(sysParts, "\n")
			}
		}
	}

	if len(request.Messages) > 0 {
		for _, m := range request.Messages {
			if m.Role == ai.RoleUser {
				parts, err := convertParts(m.Content)
				if err != nil {
					return nil, err
				}
				userParts = append(userParts, &genai.Content{
					Role:  "user",
					Parts: parts,
				})
				break
			}
		}
	}

	if systemInstruction == "" && len(userParts) == 0 {
		return nil, fmt.Errorf("no content to cache")
	}

	content := &genai.CachedContent{
		Model: modelVersion,
		SystemInstruction: &genai.Content{
			Role:  "system",
			Parts: []genai.Part{genai.Text(systemInstruction)},
		},
		Contents:   userParts,
		Expiration: genai.ExpireTimeOrTTL{TTL: calculateTTL(cacheConfig.TTL)},
	}

	return content, nil
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

// getKeysFrom returns the keys from the given map as a slice of strings, it is using to get the supported models
func getKeysFrom(m map[string]ai.ModelCapabilities) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	return keys
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

// validateContextCacheRequest decides if we should try caching for this request.
// For demonstration, we will cache if there are more than 2 messages or if there's a system prompt.
func validateContextCacheRequest(request *ai.ModelRequest, modelVersion string) error {
	models := getKeysFrom(knownCaps)
	if modelVersion == "" || !contains(models, modelVersion) {
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

	for i := len(request.Messages) - 1; i >= 0; i-- {
		m := request.Messages[i]
		if m.Metadata != nil {
			if c, ok := m.Metadata["cache"]; ok && c != nil {
				// Found a message with `metadata.cache`
				endOfCachedContents = i

				// Parse the cache config. The TS code uses zod schema;
				// here we assume `cache` can be either a boolean or a map with `ttlSeconds`.
				switch val := c.(type) {
				case bool:
					// If it's just a boolean, true = default TTL, false = no cache
					if val {
						cacheConfig = &CacheConfigDetails{
							TTL: 0, // use default if 0
						}
					} else {
						// false means no caching
						cacheConfig = &CacheConfigDetails{
							TTL: 0,
						}
					}

				case map[string]interface{}:
					ttl := time.Duration(0)
					if ttlVal, ok := val["ttlSeconds"].(float64); ok {
						ttl = time.Duration(ttlVal)
					}
					cacheConfig = &CacheConfigDetails{
						TTL: ttl,
					}

				default:
					return -1, nil, fmt.Errorf("invalid cache config type: %T", val)
				}
				break
			}
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

	if cacheConfig == nil || validateContextCacheRequest(request, modelVersion) != nil {
		return nil, nil
	}
	cachedContent, err := getContentForCache(request, modelVersion, cacheConfig)
	if err != nil || cachedContent == nil {
		return nil, nil
	}

	cachedContent.Model = modelVersion
	cacheKey := generateCacheKey(cachedContent)
	newCache, err := client.CreateCachedContent(ctx, cachedContent)
	if err != nil {
		if strings.Contains(err.Error(), "The minimum token count to start caching is 32768.") {
			slog.Debug("not enough token count to start caching: %s cacheKey: %s", err.Error(), cacheKey)
			return nil, nil
		}
		return nil, fmt.Errorf("failed to create cache: %w", err)
	}
	return newCache, nil
}

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
//
// SPDX-License-Identifier: Apache-2.0

package googlegenai

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"

	"github.com/firebase/genkit/go/ai"
	"google.golang.org/genai"
)

const cacheContentsPerPage = 5

var invalidArgMessages = struct {
	modelVersion string
	tools        string
	systemPrompt string
}{
	tools:        "tools are not supported with context caching",
	systemPrompt: "system prompts are not supported with context caching",
}

// handleCache checks if caching should be used, attempts to find or create the cache,
// and returns the cached content if applicable.
func handleCache(
	ctx context.Context,
	client *genai.Client,
	request *ai.ModelRequest,
	model string,
) (*genai.CachedContent, error) {
	cs, err := findCacheMarker(request)
	if err != nil {
		return nil, err
	}
	if cs == nil {
		return nil, nil
	}
	// no cache mark found
	if cs.endIndex == -1 {
		return nil, err
	}
	// index out of bounds
	if cs.endIndex < 0 || cs.endIndex >= len(request.Messages) {
		return nil, fmt.Errorf("end of cached contents, index %d is invalid", cs.endIndex)
	}

	err = validateContextCacheRequest(request)
	if err != nil {
		return nil, err
	}

	messages, err := messagesToCache(request.Messages, cs.endIndex)
	if err != nil {
		return nil, err
	}
	hash := calculateCacheHash(messages)

	var cache *genai.CachedContent
	if cs.name != "" {
		cache, err = lookupCache(ctx, client, cs.name)
		if err != nil {
			// TODO: if cache expired or not found, create a fresh one
			return nil, fmt.Errorf("cache lookup error, got %v", err)
		}
		// make sure the cache contents matches the request messages hash
		if cache.DisplayName != hash {
			return nil, fmt.Errorf("invalid cache name: hash mismatch between cached content and request messages")
		}

		return cache, nil
	}

	if cs.ttl > 0 {
		cache, err = client.Caches.Create(ctx, model, &genai.CreateCachedContentConfig{
			DisplayName: hash,
			TTL:         time.Duration(cs.ttl) * time.Second,
			Contents:    messages,
		})
		if err != nil {
			return nil, fmt.Errorf("cache creation error, got %v", err)
		}
	}

	return cache, nil
}

// messagesToCache collects all the messages that should be cached
func messagesToCache(m []*ai.Message, cacheEndIdx int) ([]*genai.Content, error) {
	var role string
	var messagesToCache []*genai.Content
	for i := cacheEndIdx; i >= 0; i-- {
		m := m[i]
		if m.Role == ai.RoleSystem {
			continue
		}
		parts, err := toGeminiParts(m.Content)
		if err != nil {
			return nil, err
		}

		role = string(ai.RoleUser)
		if i == cacheEndIdx {
			role = string(ai.RoleModel)
		}

		messagesToCache = append(messagesToCache, &genai.Content{
			Parts: parts,
			Role:  role,
		})
	}
	return messagesToCache, nil
}

// validateContextCacheRequest checks if Tools or SystemInstructions
// are being provided in the request
func validateContextCacheRequest(request *ai.ModelRequest) error {
	if len(request.Tools) > 0 {
		return fmt.Errorf("%s", invalidArgMessages.tools)
	}
	for _, m := range request.Messages {
		if m.Role == ai.RoleSystem {
			return fmt.Errorf("%s", invalidArgMessages.systemPrompt)
		}
	}

	return nil
}

type cacheSettings struct {
	ttl      int
	name     string
	endIndex int
}

// findCacheMarker finds the cache mark in the list of request messages.
// All of the messages preceding this mark will be cached.
func findCacheMarker(request *ai.ModelRequest) (*cacheSettings, error) {
	var cacheName string

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
			return nil, fmt.Errorf("cache metadata should be map but got: %T", cacheVal)
		}

		// cache name should be only used to indicate the request already
		// generated a cache
		if n, ok := c["name"].(string); ok {
			cacheName = n
			continue
		}

		if t, ok := c["ttlSeconds"].(int); ok {
			if m.Text() == "" {
				return nil, fmt.Errorf("no content to cache, message is empty")
			}
			return &cacheSettings{
				ttl:      t,
				name:     cacheName,
				endIndex: i,
			}, nil
		}

		return nil, fmt.Errorf("invalid type for cache ttlSeconds, expected int, got %T", c["ttlSeconds"])
	}
	return nil, nil
}

// lookupCache retrieves a *genai.CachedContent from a given cache name
func lookupCache(ctx context.Context, client *genai.Client, name string) (*genai.CachedContent, error) {
	if name == "" {
		return nil, fmt.Errorf("empty cache name detected")
	}

	return client.Caches.Get(ctx, name, nil)
}

// calculateCacheKey generates a sha256 key for cached content used to
// validate the proper usage of the requested cache
func calculateCacheHash(content []*genai.Content) string {
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

// cacheMetadata writes in the metadata map the cache name used in the
// request
func cacheMetadata(m map[string]any, cc *genai.CachedContent) map[string]any {
	// keep the original metadata if no cache was used in the request
	if cc == nil {
		return m
	}

	cache, ok := m["cache"].(map[string]any)
	if !ok {
		m = map[string]any{
			"cache": map[string]any{
				"name": cc.Name,
			},
		}
		return m
	}

	cache["name"] = cc.Name
	return m
}

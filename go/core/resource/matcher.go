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

package resource

import (
	"fmt"
	"strings"

	"github.com/yosida95/uritemplate/v3"
)

// URIMatcher handles URI matching for resources.
// This is an internal interface used by resource implementations.
type URIMatcher interface {
	Matches(uri string) bool
	ExtractVariables(uri string) (map[string]string, error)
}

// normalizeURI cleans up a URI for template matching by removing common user issues:
// - Query parameters: "api://search/hello?limit=10" → "api://search/hello"
// - Trailing slashes: "api://users/123/" → "api://users/123"
// - URI fragments: "docs://page/intro#section1" → "docs://page/intro"
// This improves user experience by making template matching more forgiving.
func normalizeURI(uri string) string {
	// Remove query parameters
	if idx := strings.Index(uri, "?"); idx != -1 {
		uri = uri[:idx]
	}

	// Remove URI fragments
	if idx := strings.Index(uri, "#"); idx != -1 {
		uri = uri[:idx]
	}

	// Remove trailing slash (but keep if it's just the root "/")
	if len(uri) > 1 && strings.HasSuffix(uri, "/") {
		uri = uri[:len(uri)-1]
	}

	return uri
}

// NewStaticMatcher creates a matcher for exact URI matches.
func NewStaticMatcher(uri string) URIMatcher {
	return &staticMatcher{uri: uri}
}

// NewTemplateMatcher creates a matcher for URI template patterns.
func NewTemplateMatcher(templateStr string) (URIMatcher, error) {
	template, err := uritemplate.New(templateStr)
	if err != nil {
		return nil, fmt.Errorf("invalid URI template %q: %w", templateStr, err)
	}
	return &templateMatcher{template: template}, nil
}

// staticMatcher matches exact URIs.
type staticMatcher struct {
	uri string
}

func (m *staticMatcher) Matches(uri string) bool {
	return m.uri == uri
}

func (m *staticMatcher) ExtractVariables(uri string) (map[string]string, error) {
	if !m.Matches(uri) {
		return nil, fmt.Errorf("URI %q does not match static URI %q", uri, m.uri)
	}
	return map[string]string{}, nil
}

// templateMatcher matches URI templates.
type templateMatcher struct {
	template *uritemplate.Template
}

func (m *templateMatcher) Matches(uri string) bool {
	cleanURI := normalizeURI(uri)
	values := m.template.Match(cleanURI)
	return len(values) > 0
}

func (m *templateMatcher) ExtractVariables(uri string) (map[string]string, error) {
	cleanURI := normalizeURI(uri)
	values := m.template.Match(cleanURI)
	if len(values) == 0 {
		return nil, fmt.Errorf("URI %q does not match template", uri)
	}

	// Convert uritemplate.Values to string map
	result := make(map[string]string)
	for name, value := range values {
		result[name] = value.String()
	}
	return result, nil
}

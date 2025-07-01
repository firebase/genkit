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

package base

import (
	"fmt"
	"net/url"
	"strings"
)

// An Environment is the execution context in which the program is running.
type Environment string

const (
	EnvironmentDev  Environment = "dev"  // development: testing, debugging, etc.
	EnvironmentProd Environment = "prod" // production: user data, SLOs, etc.
)

// Zero returns the Zero value for T.
func Zero[T any]() T {
	var z T
	return z
}

// Clean returns a valid filename for id.
func Clean(id string) string {
	return url.PathEscape(id)
}

// ParseActionKey parses an action key in the format "/<action_type>/<provider>/<name>", "/<action_type>/<name>",
// "<action_type>/<provider>/<name>", or "<action_type>/<name>".
// Returns the action type, provider (empty string if not present), and name.
// If the key format is invalid, returns an error.
func ParseActionKey(key string) (actionType, provider, name string, err error) {
	// Strip leading "/" if present since action keys typically start with "/"
	keyToParse := key
	if strings.HasPrefix(key, "/") {
		keyToParse = key[1:]
	}

	parts := strings.Split(keyToParse, "/")
	if len(parts) < 2 {
		return "", "", "", fmt.Errorf("action key must have at least 2 parts, got %d", len(parts))
	}

	actionType = parts[0]

	if len(parts) == 2 {
		// Format: <action_type>/<name>
		name = parts[1]
	} else if len(parts) == 3 {
		// Format: <action_type>/<provider>/<name>
		provider = parts[1]
		name = parts[2]
	} else {
		return "", "", "", fmt.Errorf("action key must have 2 or 3 parts, got %d", len(parts))
	}

	return actionType, provider, name, nil
}

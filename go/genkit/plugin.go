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

package genkit

import (
	"context"

	"github.com/firebase/genkit/go/core"
)

// Plugin is the interface implemented by types that extend Genkit's functionality.
// Plugins are typically used to integrate external services like model providers,
// vector databases, or monitoring tools.
// They are registered and initialized via [WithPlugins] during [Init].
type Plugin interface {
	// Name returns the unique identifier for the plugin.
	// This name is used for registration and lookup.
	Name() string
	// Init initializes the plugin. It is called once during [Init].
	// The plugin can use the provided [Genkit] instance to register actions,
	// models, tools, etc.
	Init(ctx context.Context, g *Genkit) error
}

// DynamicPlugin is a [Plugin] that can dynamically resolve actions.
type DynamicPlugin interface {
	Plugin
	// ListActions returns a list of action descriptors that the plugin is capable of resolving to [core.Action]s.
	ListActions(ctx context.Context) []core.ActionDesc
	// ResolveAction resolves an action type and name by defining and registering it in the registry.
	ResolveAction(g *Genkit, atype core.ActionType, name string) error
}

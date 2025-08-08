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

package registry

import (
	"fmt"
	"log/slog"
	"maps"
	"os"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/core/tracing"
	"github.com/google/dotprompt/go/dotprompt"
)

// This file implements registries of actions and other values.

const (
	DefaultModelKey = "genkit/defaultModel"
	PromptDirKey    = "genkit/promptDir"
)

// ActionResolver is a function type for resolving actions dynamically
type ActionResolver = func(actionType, provider, name string) error

// Registry holds all registered actions and associated types,
// and provides methods to register, query, and look up actions.
type Registry struct {
	tstate  *tracing.State
	mu      sync.Mutex
	frozen  bool           // when true, no more additions
	parent  *Registry      // parent registry for hierarchical lookups
	actions map[string]any // Values follow interface core.Action but we can't reference it here.
	plugins map[string]any // Values follow interface genkit.Plugin but we can't reference it here.
	values  map[string]any // Values can truly be anything.

	ActionResolver ActionResolver // Function for resolving actions dynamically.
	Dotprompt      *dotprompt.Dotprompt
}

// New creates a new root registry.
func New() (*Registry, error) {
	r := &Registry{
		actions: map[string]any{},
		plugins: map[string]any{},
		values:  map[string]any{},
	}
	r.tstate = tracing.NewState()
	if os.Getenv("GENKIT_TELEMETRY_SERVER") != "" {
		r.tstate.WriteTelemetryImmediate(tracing.NewHTTPTelemetryClient(os.Getenv("GENKIT_TELEMETRY_SERVER")))
	}
	r.Dotprompt = dotprompt.NewDotprompt(&dotprompt.DotpromptOptions{
		Helpers:  make(map[string]any),
		Partials: make(map[string]string),
	})
	return r, nil
}

// NewChild creates a new child registry that inherits from this registry.
// Child registries are cheap to create and will fall back to the parent
// for lookups if a value is not found in the child.
func (r *Registry) NewChild() *Registry {
	child := &Registry{
		parent:         r,
		tstate:         r.tstate,
		actions:        map[string]any{},
		plugins:        map[string]any{},
		values:         map[string]any{},
		ActionResolver: r.ActionResolver,
		Dotprompt:      r.Dotprompt,
	}
	return child
}

func (r *Registry) TracingState() *tracing.State { return r.tstate }

// RegisterPlugin records the plugin in the registry.
// It panics if a plugin with the same name is already registered.
func (r *Registry) RegisterPlugin(name string, p any) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.plugins[name]; ok {
		panic(fmt.Sprintf("plugin %q is already registered", name))
	}
	r.plugins[name] = p
	slog.Debug("RegisterPlugin", "name", name)
}

// RegisterAction records the action in the registry.
// It panics if an action with the same type, provider and name is already
// registered.
func (r *Registry) RegisterAction(key string, action any) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.actions[key]; ok {
		panic(fmt.Sprintf("action %q is already registered", key))
	}
	r.actions[key] = action
	slog.Debug("RegisterAction", "key", key)
}

// LookupPlugin returns the plugin for the given name.
// It first checks the current registry, then falls back to the parent if not found.
// Returns nil if the plugin is not found in the registry hierarchy.
func (r *Registry) LookupPlugin(name string) any {
	r.mu.Lock()
	defer r.mu.Unlock()

	if plugin, ok := r.plugins[name]; ok {
		return plugin
	}

	if r.parent != nil {
		return r.parent.LookupPlugin(name)
	}

	return nil
}

// RegisterValue records an arbitrary value in the registry.
// It panics if a value with the same name is already registered.
func (r *Registry) RegisterValue(name string, value any) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, ok := r.values[name]; ok {
		panic(fmt.Sprintf("value %q is already registered", name))
	}
	r.values[name] = value
	slog.Debug("RegisterValue", "name", name)
}

// LookupValue returns the value for the given name.
// It first checks the current registry, then falls back to the parent if not found.
// Returns nil if the value is not found in the registry hierarchy.
func (r *Registry) LookupValue(name string) any {
	r.mu.Lock()
	defer r.mu.Unlock()

	if value, ok := r.values[name]; ok {
		return value
	}

	if r.parent != nil {
		return r.parent.LookupValue(name)
	}

	return nil
}

// LookupAction returns the action for the given key.
// It first checks the current registry, then falls back to the parent if not found.
func (r *Registry) LookupAction(key string) any {
	r.mu.Lock()
	defer r.mu.Unlock()

	if action, ok := r.actions[key]; ok {
		return action
	}

	if r.parent != nil {
		return r.parent.LookupAction(key)
	}

	return nil
}

// ResolveAction looks up an action by key. If the action is not found, it attempts dynamic resolution.
// Returns the action if found, or nil if not found.
func (r *Registry) ResolveAction(key string) any {
	action := r.LookupAction(key)
	if action == nil && r.ActionResolver != nil {
		typ, provider, name, err := ParseActionKey(key)
		if err != nil {
			slog.Debug("ResolveAction: failed to parse action key", "key", key, "err", err)
			return nil
		}
		err = r.ActionResolver(typ, provider, name)
		if err != nil {
			// TODO: Handle errors from the action resolver better.
			slog.Error("ResolveAction: failed to resolve action", "key", key, "err", err)
			return nil
		}
		action = r.LookupAction(key)
	}
	return action
}

// ListActions returns a list of all registered actions.
// This includes actions from both the current registry and its parent hierarchy.
// Child registry actions take precedence over parent actions with the same key.
func (r *Registry) ListActions() []any {
	r.mu.Lock()
	defer r.mu.Unlock()
	var actions []any
	for _, v := range r.actions {
		actions = append(actions, v)
	}
	return actions
}

// ListPlugins returns a list of all registered plugins.
func (r *Registry) ListPlugins() []any {
	r.mu.Lock()
	defer r.mu.Unlock()
	var plugins []any
	for _, p := range r.plugins {
		plugins = append(plugins, p)
	}
	return plugins
}

// ListValues returns a list of values of all registered values.
// This includes values from both the current registry and its parent hierarchy.
// Child registry values take precedence over parent values with the same key.
func (r *Registry) ListValues() map[string]any {
	r.mu.Lock()
	defer r.mu.Unlock()

	allValues := make(map[string]any)

	if r.parent != nil {
		parentValues := r.parent.ListValues()
		maps.Copy(allValues, parentValues)
	}

	maps.Copy(allValues, r.values)

	return allValues
}

// An Environment is the execution context in which the program is running.
type Environment string

const (
	EnvironmentDev  Environment = "dev"  // development: testing, debugging, etc.
	EnvironmentProd Environment = "prod" // production: user data, SLOs, etc.
)

// CurentEnvironment returns the currently active environment.
func CurrentEnvironment() Environment {
	if v := os.Getenv("GENKIT_ENV"); v != "" {
		return Environment(v)
	}
	return EnvironmentProd
}

// DefinePartial adds the partial to the list of partials to the dotprompt instance
func (r *Registry) DefinePartial(name string, source string) error {
	if r.Dotprompt == nil {
		r.Dotprompt = dotprompt.NewDotprompt(&dotprompt.DotpromptOptions{
			Partials: map[string]string{},
		})
	}
	if r.Dotprompt.Partials == nil {
		r.Dotprompt.Partials = make(map[string]string)
	}

	if r.Dotprompt.Partials[name] != "" {
		return fmt.Errorf("partial %q is already defined", name)
	}
	r.Dotprompt.Partials[name] = source
	return nil
}

// DefineHelper adds a helper function to the dotprompt instance
func (r *Registry) DefineHelper(name string, fn any) error {
	if r.Dotprompt == nil {
		r.Dotprompt = dotprompt.NewDotprompt(&dotprompt.DotpromptOptions{
			Helpers: map[string]any{},
		})
	}
	if r.Dotprompt.Helpers == nil {
		r.Dotprompt.Helpers = make(map[string]any)
	}

	if r.Dotprompt.Helpers[name] != nil {
		return fmt.Errorf("helper %q is already defined", name)
	}
	r.Dotprompt.Helpers[name] = fn
	return nil
}

// ParseActionKey parses an action key in the format "/<action_type>/<provider>/<name>" or "/<action_type>/<name>".
// Returns the action type, provider (empty string if not present), and name.
// If the key format is invalid, returns an error.
func ParseActionKey(key string) (actionType, provider, name string, err error) {
	if !strings.HasPrefix(key, "/") {
		return "", "", "", fmt.Errorf("action key must start with '/', got %q", key)
	}

	parts := strings.Split(key[1:], "/")
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

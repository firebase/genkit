// Copyright 2026 Google LLC
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

package exp

import (
	"regexp"
	"slices"
	"strings"
)

// baseEnv matches the inherited vars a box keeps even when it inherits
// nothing else: what a runtime needs to start (PATH, locale, temp dirs, CA
// certs, the Go toolchain's own settings for "go run" entries), plus the
// caller's run mode (GENKIT_ENV) and, under "genkit start", where to export
// traces (GENKIT_TELEMETRY_SERVER). The box's own reflection vars are set by
// the runner, never inherited.
var baseEnv = []*regexp.Regexp{
	regexp.MustCompile(`^(PATH|HOME|USER|LOGNAME|SHELL|TMPDIR|TMP|TEMP|LANG|TZ|TERM)$`),
	regexp.MustCompile(`^LC_`),
	regexp.MustCompile(`^(GOCACHE|GOPATH|GOMODCACHE|GOFLAGS|GOTOOLCHAIN|GOROOT|GOPROXY|GOPRIVATE|GONOSUMDB)$`),
	regexp.MustCompile(`^(SSL_CERT_FILE|SSL_CERT_DIR)$`),
	regexp.MustCompile(`^GENKIT_(ENV|TELEMETRY_SERVER)$`),
	// Windows: process creation and temp/home resolution. Names there are
	// case-insensitive (Path, SystemRoot).
	regexp.MustCompile(`(?i)^(PATH|PATHEXT|SYSTEMROOT|COMSPEC|USERPROFILE|APPDATA|LOCALAPPDATA)$`),
}

// InheritEnv says which of the caller's env vars a box inherits; see
// [WithInheritEnv].
type InheritEnv struct {
	all   bool
	names []string
}

// InheritAll inherits every env var, API keys included (the default).
func InheritAll() InheritEnv { return InheritEnv{all: true} }

// InheritBase inherits only the basics a runtime needs to start (PATH, HOME,
// locale, temp dirs, the Go toolchain's settings, GENKIT_ENV, ...), plus
// the named vars.
//
//	box.WithInheritEnv(box.InheritBase("GEMINI_API_KEY"))
func InheritBase(names ...string) InheritEnv { return InheritEnv{names: names} }

// childEnv builds a box's environment, lowest precedence first: the filtered
// parent env, then env, then overrides (the runner's own vars, which must win
// so a user value cannot break the link to the host).
func childEnv(parent []string, inherit InheritEnv, env, overrides map[string]string) []string {
	vals := map[string]string{}
	var order []string
	set := func(k, v string) {
		if _, ok := vals[k]; !ok {
			order = append(order, k)
		}
		vals[k] = v
	}
	for _, kv := range parent {
		k, v, ok := strings.Cut(kv, "=")
		if !ok || k == "" {
			continue
		}
		if inherit.all || slices.Contains(inherit.names, k) || slices.ContainsFunc(baseEnv, func(re *regexp.Regexp) bool { return re.MatchString(k) }) {
			set(k, v)
		}
	}
	for _, m := range []map[string]string{env, overrides} {
		keys := make([]string, 0, len(m))
		for k := range m {
			keys = append(keys, k)
		}
		slices.Sort(keys)
		for _, k := range keys {
			set(k, m[k])
		}
	}
	out := make([]string, len(order))
	for i, k := range order {
		out[i] = k + "=" + vals[k]
	}
	return out
}

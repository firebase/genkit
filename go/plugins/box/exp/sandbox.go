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

// SpawnSpec is the command a runner starts for one box, before isolation.
type SpawnSpec struct {
	// Path is the program to run.
	Path string
	// Args are its arguments, without the program name.
	Args []string
	// Env is the complete environment, as KEY=value pairs.
	Env []string
	// Dir is the working directory; empty means the current one.
	Dir string
}

// ReflectHost is where the box's reflection host listens: what the box dials.
type ReflectHost struct {
	// URL is the WebSocket URL, e.g. ws://127.0.0.1:54321.
	URL string
	// Port is its loopback port.
	Port int
}

// PreparedSpawn is the isolated command a [SandboxProvider] produces.
type PreparedSpawn struct {
	SpawnSpec
	// ReflectURL is the URL the box should dial; usually ReflectHost.URL.
	ReflectURL string
}

// SandboxProvider isolates the processes an [ExecRunner] starts, passed with
// [WithIsolation]. It transforms the base command into the isolated one, and
// must leave the box a way to reach the reflection host on loopback.
type SandboxProvider interface {
	// Name identifies the provider in logs and errors.
	Name() string
	// Prepare returns the isolated command for spec.
	Prepare(spec SpawnSpec, host ReflectHost) (PreparedSpawn, error)
}

// subprocess is the default provider: the command as is, no isolation.
type subprocess struct{}

func (subprocess) Name() string { return "subprocess" }

func (subprocess) Prepare(spec SpawnSpec, host ReflectHost) (PreparedSpawn, error) {
	return PreparedSpawn{SpawnSpec: spec, ReflectURL: host.URL}, nil
}

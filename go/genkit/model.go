// Copyright 2024 Google LLC
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

package genkit

type ModelStage int

/** At which stage of development the model is.
 * - `featured` models are recommended for general use.
 * - `stable` models are well-tested and reliable.
 * - `unstable` models are experimental and may change.
 * - `legacy` models are no longer recommended for new projects.
 * - `deprecated` models are deprecated by the provider and may be removed in future versions.
 */
const (
	FEATURED ModelStage = iota
	STABLE
	UNSTABLE
	LEGACY
	DEPRECATED
)

type ModelCapabilities struct {
	/** Model can output this type of data. */
	Output []string
	/** Model supports output in these content types. */
	ContentType []string
	/** Model can process historical messages passed with a prompt. */
	Multiturn bool
	/** Model can process media as part of the prompt (multimodal input). */
	Media bool
	/** Model can perform tool calls. */
	Tools bool
	/** Model can accept messages with role "system". */
	SystemRole bool
	/** Model can natively support document-based context grounding. */
	Context bool
}

type ModelInfo struct {
	Versions []string
	Label    string
	Supports ModelCapabilities
	// TODO: is Stage needed?
	Stage ModelStage
}

type ModelReference struct {
	Name    string
	Version string
	Info    ModelInfo
	// TODO: configSchema and config should be something
}

type ModelOptions func(*ModelReference)

func WithVersion(version string) ModelOptions {
	return func(m *ModelReference) {
		m.Version = version
	}
}

func ModelRef(opts ...ModelOptions) *ModelReference {
	m := &ModelReference{}
	for _, opt := range opts {
		opt(m)
	}

	return m
}

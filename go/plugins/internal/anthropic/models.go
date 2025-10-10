// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/internal"
)

var anthropicModels = map[string]ai.ModelOptions{
	"claude-3-5-sonnet-v2": {
		Label:    "Claude 3.5 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-5-sonnet-v2@20241022"},
	},
	"claude-3-5-sonnet": {
		Label:    "Claude 3.5 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-5-sonnet@20240620"},
	},
	"claude-3-sonnet": {
		Label:    "Claude 3 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-sonnet@20240229"},
	},
	"claude-3-haiku": {
		Label:    "Claude 3 Haiku",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-haiku@20240307"},
	},
	"claude-3-opus": {
		Label:    "Claude 3 Opus",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-opus@20240229"},
	},
	"claude-3-7-sonnet": {
		Label:    "Claude 3.7 Sonnet",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-3-7-sonnet@20250219"},
	},
	"claude-opus-4": {
		Label:    "Claude Opus 4",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-opus-4@20250514"},
	},
	"claude-sonnet-4": {
		Label:    "Claude Sonnet 4",
		Supports: &internal.Multimodal,
		Versions: []string{"claude-sonnet-4@20250514"},
	},
}

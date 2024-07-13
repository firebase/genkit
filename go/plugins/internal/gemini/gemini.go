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

// Package gemini contains code that is common to both the googleai and vertexai plugins.
// Most most cannot be shared in this way because the import paths are different.
package gemini

import "github.com/firebase/genkit/go/ai"

var (
	// BasicText describes model capabilities for text-only Gemini models.
	BasicText = ai.ModelCapabilities{
		Multiturn:  true,
		Tools:      true,
		SystemRole: true,
		Media:      false,
	}

	//  Multimodal describes model capabilities for multimodal Gemini models.
	Multimodal = ai.ModelCapabilities{
		Multiturn:  true,
		Tools:      true,
		SystemRole: true,
		Media:      true,
	}
)

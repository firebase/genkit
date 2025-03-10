// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package gemini contains code that is common to both the googleai and vertexai plugins.
// Most most cannot be shared in this way because the import paths are different.
package gemini

import "github.com/firebase/genkit/go/ai"

var (
	// BasicText describes model capabilities for text-only Gemini models.
	BasicText = ai.ModelInfoSupports{
		Multiturn:  true,
		Tools:      true,
		ToolChoice: true,
		SystemRole: true,
		Media:      false,
	}

	//  Multimodal describes model capabilities for multimodal Gemini models.
	Multimodal = ai.ModelInfoSupports{
		Multiturn:  true,
		Tools:      true,
		ToolChoice: true,
		SystemRole: true,
		Media:      true,
	}
)

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

package googlegenai

import (
	"context"
	"encoding/base64"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"google.golang.org/genai"
)

var (
	// BasicMedia describes model capabitities for image-only output Gemini models.
	BasicMedia = ai.ModelSupports{
		Media:      false,
		Multiturn:  false,
		Tools:      false,
		ToolChoice: false,
		SystemRole: false,
	}

	// Media describes model capabilities for Gemini models with media and text
	// input and image only output
	Media = ai.ModelSupports{
		Media:      true,
		Multiturn:  false,
		Tools:      false,
		ToolChoice: false,
		SystemRole: false,
	}
)

type PersonGeneration string

const (
	// Disallow the inclusion of people or faces in images
	DontAllowPerson PersonGeneration = "dont_allow"
	// Allow generation of adults only
	AllowAdultPerson PersonGeneration = "allow_adult"
	// Allow generation of people of all ages
	AllowAllPerson PersonGeneration = "allow_all"
)

// Enum that specifies the language of the text in the prompt.
type ImagePromptLanguage string

const (
	ImagePromptLanguageAuto ImagePromptLanguage = "auto"
	ImagePromptLanguageEn   ImagePromptLanguage = "en"
	ImagePromptLanguageJa   ImagePromptLanguage = "ja"
	ImagePromptLanguageKo   ImagePromptLanguage = "ko"
	ImagePromptLanguageHi   ImagePromptLanguage = "hi"
)

// Imagen generation configuration
// VertexAI API default values: https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/imagen-api
// GeminiAPI: https://ai.google.dev/gemini-api/docs/imagen#imagen-model
type ImagenConfig struct {
	// Number of images to generate. Defaults to 4
	NumberOfImages int32 `json:"numberOfImages,omitempty"`
	// Random seed generation
	Seed *int32 `json:"seed,omitempty"`
	// A description of what to discourage in the generated images
	NegativePrompt string `json:"negativePrompt,omitempty"`
	// Aspect ratio for the image. Defaults to 1:1
	AspectRatio string `json:"aspectRatio,omitempty"`
	// Allow generation of people by the model. Defaults to [AllowAdultPerson]
	PersonGeneration PersonGeneration `json:"personGeneration,omitempty"`
	// Language of the text in the prompt
	Language string `json:"language,omitempty"`
	// Filter level to safety filtering
	SafetySetting HarmBlockThreshold `json:"safetySetting,omitempty"`
	// Sets an invisible watermark to the generated images
	AddWatermark bool `json:"addWatermark,omitempty"`
	// Cloud Storage URI used to store the generated images.
	OutputGCSURI string `json:"outputGcsUri,omitempty"`
	// MIME type of the generated image.
	OutputMIMEType string `json:"outputMimeType,omitempty"`
}

func imagenConfigFromRequest(input *ai.ModelRequest) (*ImagenConfig, error) {
	var result ImagenConfig

	switch config := input.Config.(type) {
	case ImagenConfig:
		result = config
	case *ImagenConfig:
		result = *config
	case map[string]any:
		if err := mapToStruct(config, &result); err != nil {
			return nil, err
		}
	case nil:
		// empty but valid config
	default:
		return nil, fmt.Errorf("unexpected config type: %T", input.Config)
	}

	return &result, nil
}

func toImageRequest(input *ai.ModelRequest) (*genai.GenerateImagesConfig, error) {
	config, err := imagenConfigFromRequest(input)
	if err != nil {
		return nil, err
	}

	gic := genai.GenerateImagesConfig{
		AddWatermark: config.AddWatermark,
	}
	if config.NumberOfImages > 0 {
		gic.NumberOfImages = config.NumberOfImages
	}
	if config.Seed != nil {
		gic.Seed = config.Seed
	}
	if config.NegativePrompt != "" {
		gic.NegativePrompt = config.NegativePrompt
	}
	if config.AspectRatio != "" {
		gic.AspectRatio = config.AspectRatio
	}
	if config.PersonGeneration != "" {
		gic.PersonGeneration = genai.PersonGeneration(config.PersonGeneration)
	}
	if config.Language != "" {
		gic.Language = genai.ImagePromptLanguage(config.Language)
	}
	if config.SafetySetting != "" {
		gic.SafetyFilterLevel = genai.SafetyFilterLevel(config.SafetySetting)
	}
	if config.OutputGCSURI != "" {
		gic.OutputGCSURI = config.OutputGCSURI
	}
	if config.OutputMIMEType != "" {
		gic.OutputMIMEType = config.OutputMIMEType
	}

	return &gic, nil
}

func translateImagenCandidates(images []*genai.GeneratedImage) *ai.ModelResponse {
	m := &ai.ModelResponse{}
	m.FinishReason = ai.FinishReasonStop

	msg := &ai.Message{}
	msg.Role = ai.RoleModel

	for _, img := range images {
		msg.Content = append(msg.Content, ai.NewMediaPart(img.Image.MIMEType, "data:"+img.Image.MIMEType+";base64,"+base64.StdEncoding.EncodeToString(img.Image.ImageBytes)))
	}

	m.Message = msg
	return m
}

func translateImagenResponse(resp *genai.GenerateImagesResponse) *ai.ModelResponse {
	return translateImagenCandidates(resp.GeneratedImages)
}

func generateImage(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	gic, err := toImageRequest(input)
	if err != nil {
		return nil, err
	}

	var userPrompt string
	for _, m := range input.Messages {
		if m.Role == ai.RoleUser {
			userPrompt += m.Text()
		}
	}
	if userPrompt == "" {
		return nil, fmt.Errorf("empty prompt detected")
	}

	if cb == nil {
		resp, err := client.Models.GenerateImages(ctx, model, userPrompt, gic)
		if err != nil {
			return nil, err
		}

		r := translateImagenResponse(resp)
		r.Request = input
		return r, nil
	}

	return nil, nil
}

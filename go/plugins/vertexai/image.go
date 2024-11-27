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

package vertexai

import (
	"cloud.google.com/go/vertexai/genai"
	"context"
	"fmt"
	"github.com/firebase/genkit/go/ai"
)

func imagenModel(
	ctx context.Context,
	client *genai.Client,
	model string,
	input *ai.ModelRequest,
	cb func(context.Context, *ai.ModelResponseChunk) error,
) (*ai.ModelResponse, error) {
	gm := client.GenerativeModel(model)

	var prompt string
	if len(input.Messages) > 0 {
		prompt = input.Messages[len(input.Messages)-1].Text()
	}

	parts := []genai.Part{genai.Text(prompt)}
	if meta, ok := input.Config.(*ImagenParameters); ok {
		if meta.NegativePrompt != "" {
			parts = append(parts, genai.Blob{
				Data:     []byte(meta.NegativePrompt),
				MIMEType: "application/x-negative-prompt",
			})
		}
	}

	resp, err := gm.GenerateContent(ctx, parts...)
	if err != nil {
		return nil, fmt.Errorf("error generating content: %w", err)
	}

	m := &ai.ModelResponse{
		Usage: &ai.GenerationUsage{
			Custom: map[string]float64{
				"promptTokenCount":     float64(resp.UsageMetadata.PromptTokenCount),
				"candidatesTokenCount": float64(resp.UsageMetadata.CandidatesTokenCount),
				"totalTokenCount":      float64(resp.UsageMetadata.TotalTokenCount),
			},
		},
	}
	for _, cand := range resp.Candidates {
		if cb != nil {
			err := cb(ctx, &ai.ModelResponseChunk{
				Content: partsFromContent(cand.Content),
			})
			if err != nil {
				return nil, err
			}
		}
		m.Message = &ai.Message{
			Role:    ai.RoleModel,
			Content: partsFromContent(cand.Content),
		}
	}
	return m, nil
}

func partsFromContent(content *genai.Content) []*ai.Part {
	var parts []*ai.Part
	for _, part := range content.Parts {
		switch p := part.(type) {
		case genai.Text:
			parts = append(parts, ai.NewTextPart(string(p)))
		case genai.FileData:
			parts = append(parts, ai.NewMediaPart(p.MIMEType, p.FileURI))
		}
	}
	return parts
}

func configFromRequest(req *ai.ModelRequest) *genai.GenerationConfig {
	config := &genai.GenerationConfig{}
	if meta, ok := req.Config.(*ImagenParameters); ok {
		config.StopSequences = []string{meta.NegativePrompt}
	}
	return config
}

type ImagenParameters struct {
	MaskImage         string `json:"maskImage,omitempty"`
	AdhereToMaskImage string `json:"adhereToMaskImage,omitempty"`
	NegativePrompt    string `json:"negativePrompt,omitempty"`
}

/*package vertexai

import (
	aiplatform "cloud.google.com/go/aiplatform/apiv1"
	"cloud.google.com/go/aiplatform/apiv1/aiplatformpb"
	"context"
	"errors"
	"fmt"
	"github.com/alonsopf/go/ai"
	"google.golang.org/protobuf/types/known/structpb"
	"strings"
)

type ImagenConfig struct {
	Language         string               `json:"language,omitempty"`
	AspectRatio      string               `json:"aspectRatio,omitempty"`
	NegativePrompt   string               `json:"negativePrompt,omitempty"`
	Seed             int                  `json:"seed,omitempty"`
	Location         string               `json:"location,omitempty"`
	PersonGeneration string               `json:"personGeneration,omitempty"`
	SafetySetting    string               `json:"safetySetting,omitempty"`
	AddWatermark     *bool                `json:"addWatermark,omitempty"`
	StorageURI       string               `json:"storageUri,omitempty"`
	Mode             string               `json:"mode,omitempty"`
	EditConfig       *ImagenEditConfig    `json:"editConfig,omitempty"`
	UpscaleConfig    *ImagenUpscaleConfig `json:"upscaleConfig,omitempty"`
}

type ImagenEditConfig struct {
	EditMode        string          `json:"editMode,omitempty"`
	MaskMode        *ImagenMaskMode `json:"maskMode,omitempty"`
	MaskDilation    int             `json:"maskDilation,omitempty"`
	GuidanceScale   float64         `json:"guidanceScale,omitempty"`
	ProductPosition string          `json:"productPosition,omitempty"`
}

type ImagenMaskMode struct {
	MaskType string `json:"maskType,omitempty"`
	Classes  []int  `json:"classes,omitempty"`
}

type ImagenUpscaleConfig struct {
	UpscaleFactor string `json:"upscaleFactor,omitempty"`
}

func generateImage(
	ctx context.Context,
	client *aiplatform.PredictionClient,
	model string,
	input *ai.ModelRequest,
	cb ai.ModelStreamingCallback,
) (*ai.ModelResponse, error) {
	// Prepare the instance and parameters based on input and ImagenConfig
	instance, parameters, err := prepareImagenRequest(input)
	if err != nil {
		return nil, err
	}

	// Create the PredictRequest
	req := &aiplatformpb.PredictRequest{
		Endpoint:   fmt.Sprintf("projects/%s/locations/%s/publishers/google/models/%s", state.projectID, state.location, model),
		Instances:  []*structpb.Value{instance},
		Parameters: parameters,
	}

	// Call the Predict method
	resp, err := client.Predict(ctx, req)
	if err != nil {
		return nil, err
	}

	// Process the response and construct ModelResponse
	return processImagenResponse(resp)
}
func processImagenResponse(resp *aiplatformpb.PredictResponse) (*ai.ModelResponse, error) {
	if len(resp.Predictions) == 0 {
		return nil, errors.New("no predictions returned")
	}

	// Initialize the Message with the role set to 'model'
	message := &ai.Message{
		Role:    ai.RoleModel,
		Content: []*ai.Part{},
	}

	// Iterate over each prediction and construct Parts
	for _, pred := range resp.Predictions {
		// Extract the image bytes and MIME type from the prediction
		predStruct := pred.GetStructValue()
		bytesBase64Encoded := predStruct.Fields["bytesBase64Encoded"].GetStringValue()
		mimeType := predStruct.Fields["mimeType"].GetStringValue()

		// Construct the data URI for the image
		dataURI := fmt.Sprintf("data:%s;base64,%s", mimeType, bytesBase64Encoded)

		// Create a Part representing the media content
		part := &ai.Part{
			Kind:        ai.PartMedia,
			ContentType: mimeType,
			Text:        dataURI,
		}

		// Append the Part to the Message's Content
		message.Content = append(message.Content, part)
	}

	// Construct the ModelResponse
	return &ai.ModelResponse{
		Message: message,
		Usage: &ai.GenerationUsage{
			OutputImages: len(resp.Predictions),
		},
		Custom: resp, // Include the raw response if needed
	}, nil
}

func imagenConfigToMap(config *ImagenConfig) map[string]interface{} {
	params := make(map[string]interface{})

	if config.Language != "" {
		params["language"] = config.Language
	}
	if config.AspectRatio != "" {
		params["aspectRatio"] = config.AspectRatio
	}
	if config.NegativePrompt != "" {
		params["negativePrompt"] = config.NegativePrompt
	}
	if config.Seed != 0 {
		params["seed"] = config.Seed
	}
	if config.Location != "" {
		params["location"] = config.Location
	}
	if config.PersonGeneration != "" {
		params["personGeneration"] = config.PersonGeneration
	}
	if config.SafetySetting != "" {
		params["safetySetting"] = config.SafetySetting
	}
	if config.AddWatermark != nil {
		params["addWatermark"] = *config.AddWatermark
	}
	if config.StorageURI != "" {
		params["storageUri"] = config.StorageURI
	}
	if config.Mode != "" {
		params["mode"] = config.Mode
	}
	// Handle EditConfig and UpscaleConfig if provided
	if config.EditConfig != nil {
		params["editConfig"] = imagenEditConfigToMap(config.EditConfig)
	}
	if config.UpscaleConfig != nil {
		params["upscaleConfig"] = imagenUpscaleConfigToMap(config.UpscaleConfig)
	}

	return params
}

func imagenEditConfigToMap(editConfig *ImagenEditConfig) map[string]interface{} {
	editConfigMap := make(map[string]interface{})
	if editConfig.EditMode != "" {
		editConfigMap["editMode"] = editConfig.EditMode
	}
	if editConfig.MaskMode != nil {
		maskModeMap := make(map[string]interface{})
		if editConfig.MaskMode.MaskType != "" {
			maskModeMap["maskType"] = editConfig.MaskMode.MaskType
		}
		if len(editConfig.MaskMode.Classes) > 0 {
			maskModeMap["classes"] = editConfig.MaskMode.Classes
		}
		editConfigMap["maskMode"] = maskModeMap
	}
	if editConfig.MaskDilation != 0 {
		editConfigMap["maskDilation"] = editConfig.MaskDilation
	}
	if editConfig.GuidanceScale != 0 {
		editConfigMap["guidanceScale"] = editConfig.GuidanceScale
	}
	if editConfig.ProductPosition != "" {
		editConfigMap["productPosition"] = editConfig.ProductPosition
	}
	return editConfigMap
}

func imagenUpscaleConfigToMap(upscaleConfig *ImagenUpscaleConfig) map[string]interface{} {
	upscaleConfigMap := make(map[string]interface{})
	if upscaleConfig.UpscaleFactor != "" {
		upscaleConfigMap["upscaleFactor"] = upscaleConfig.UpscaleFactor
	}
	return upscaleConfigMap
}
func processImagenResponse(resp *aiplatformpb.PredictResponse) (*ai.ModelResponse, error) {
	if len(resp.Predictions) == 0 {
		return nil, errors.New("no predictions returned")
	}

	// Initialize the Message with the role set to 'model'
	message := &ai.Message{
		Role:    ai.RoleModel,
		Content: []*ai.Part{},
	}

	// Iterate over each prediction and construct Parts
	for _, pred := range resp.Predictions {
		// Extract the image bytes and MIME type from the prediction
		predStruct := pred.GetStructValue()
		bytesBase64Encoded := predStruct.Fields["bytesBase64Encoded"].GetStringValue()
		mimeType := predStruct.Fields["mimeType"].GetStringValue()

		// Construct the data URI for the image
		mediaURL := fmt.Sprintf("data:%s;base64,%s", mimeType, bytesBase64Encoded)

		// Create a Part representing the media content
		part := &ai.Part{
			Data: mediaURL,
			Metadata: map[string]any{
				"contentType": mimeType,
				"type":        "media",
			},
		}

		// Append the Part to the Message's Content
		message.Content = append(message.Content, part)
	}

	// Construct the ModelResponse
	return &ai.ModelResponse{
		Message: message,
		Usage: &ai.GenerationUsage{
			OutputImages: len(resp.Predictions),
		},
		Custom: resp, // Include the raw response if needed
	}, nil
}

func extractText(req *ai.ModelRequest) string {
	if len(req.Messages) == 0 {
		return ""
	}
	lastMessage := req.Messages[len(req.Messages)-1]
	var prompt string
	for _, content := range lastMessage.Content {
		if content.IsText() {
			prompt += content.Text
		}
	}
	return prompt
}
func extractBaseImage(req *ai.ModelRequest) (string, error) {
	if len(req.Messages) == 0 {
		return "", nil
	}
	lastMessage := req.Messages[len(req.Messages)-1]
	for _, content := range lastMessage.Content {
		if content.IsMedia() && content.Metadata["type"] == "base" {
			dataURI := content.Media.URL
			return extractBase64Data(dataURI)
		}
	}
	return "", nil
}

func extractMaskImage(req *ai.ModelRequest) (string, error) {
	if len(req.Messages) == 0 {
		return "", nil
	}
	lastMessage := req.Messages[len(req.Messages)-1]
	for _, content := range lastMessage.Content {
		if content.IsMedia() && content.Metadata["type"] == "mask" {
			dataURI := content.Media.URL
			return extractBase64Data(dataURI)
		}
	}

	return "", nil
}

func extractBase64Data(dataURI string) (string, error) {
	parts := strings.SplitN(dataURI, ",", 2)
	if len(parts) != 2 {
		return "", errors.New("invalid data URI")
	}
	return parts[1], nil
}
*/

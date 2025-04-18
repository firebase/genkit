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

package ai

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"slices"
	"strconv"
	"strings"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
)

// AugmentWithContextOptions configures how a request is augmented with context.
type AugmentWithContextOptions struct {
	Preface      *string                                                                // Preceding text to place before the rendered context documents.
	ItemTemplate func(d Document, index int, options *AugmentWithContextOptions) string // A function to render a document into a text part to be included in the message.
	CitationKey  *string                                                                // Metadata key to use for citation reference. Pass `nil` to provide no citations.
}

// contextPreface is the default preface for context augmentation.
const contextPreface = "\n\nUse the following information to complete your task:\n\n"

// DownloadMediaOptions configures how media is downloaded in the [DownloadRequestMedia] middleware.
type DownloadMediaOptions struct {
	MaxBytes int64                 // Maximum number of bytes to download.
	Filter   func(part *Part) bool // Filter to apply to parts that are media URLs.
}

// simulateSystemPrompt provides a simulated system prompt for models that don't support it natively.
func simulateSystemPrompt(info *ModelInfo, options map[string]string) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			// Short-circuiting middleware if system role is supported in model.
			if info.Supports.SystemRole {
				return next(ctx, input, cb)
			}
			preface := "SYSTEM INSTRUCTIONS:\n"
			acknowledgement := "Understood."

			if options != nil {
				if p, ok := options["preface"]; ok {
					preface = p
				}
				if a, ok := options["acknowledgement"]; ok {
					acknowledgement = a
				}
			}
			modifiedMessages := make([]*Message, len(input.Messages))
			copy(modifiedMessages, input.Messages)
			for i, message := range input.Messages {
				if message.Role == "system" {
					systemPrompt := message.Content
					userMessage := &Message{
						Role:    "user",
						Content: append([]*Part{NewTextPart(preface)}, systemPrompt...),
					}
					modelMessage := NewModelTextMessage(acknowledgement)

					modifiedMessages = append(modifiedMessages[:i], append([]*Message{userMessage, modelMessage}, modifiedMessages[i+1:]...)...)
					break
				}
			}
			input.Messages = modifiedMessages
			return next(ctx, input, cb)
		}
	}
}

// validateSupport validates whether a model supports the features used in the model request.
func validateSupport(model string, info *ModelInfo) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			if info == nil {
				info = &ModelInfo{
					Supports: &ModelSupports{},
					Versions: []string{},
				}
			}

			if !info.Supports.Media {
				for _, msg := range input.Messages {
					for _, part := range msg.Content {
						if part.IsMedia() {
							return nil, core.NewError(core.INVALID_ARGUMENT, "model %q does not support media, but media was provided. Request: %+v", model, input)
						}
					}
				}
			}

			if !info.Supports.Tools && len(input.Tools) > 0 {
				return nil, core.NewError(core.INVALID_ARGUMENT, "model %q does not support tool use, but tools were provided. Request: %+v", model, input)
			}

			if !info.Supports.Multiturn && len(input.Messages) > 1 {
				return nil, core.NewError(core.INVALID_ARGUMENT, "model %q does not support multiple messages, but %d were provided. Request: %+v", model, len(input.Messages), input)
			}

			if !info.Supports.ToolChoice && input.ToolChoice != "" && input.ToolChoice != ToolChoiceAuto {
				return nil, core.NewError(core.INVALID_ARGUMENT, "model %q does not support tool choice, but tool choice was provided. Request: %+v", model, input)
			}

			if !info.Supports.SystemRole {
				for _, msg := range input.Messages {
					if msg.Role == RoleSystem {
						return nil, core.NewError(core.INVALID_ARGUMENT, "model %q does not support system role, but system role was provided. Request: %+v", model, input)
					}
				}
			}

			if info.Stage != "" {
				switch info.Stage {
				case ModelStageDeprecated:
					logger.FromContext(ctx).Warn("model is deprecated and may be removed in a future release", "model", model)
				case ModelStageUnstable:
					logger.FromContext(ctx).Info("model is experimental or unstable", "model", model)
				}
			}

			if (info.Supports.Constrained == "" ||
				info.Supports.Constrained == ConstrainedSupportNone ||
				(info.Supports.Constrained == ConstrainedSupportNoTools && len(input.Tools) > 0)) &&
				input.Output != nil && input.Output.Constrained {
				return nil, core.NewError(core.INVALID_ARGUMENT, "model %q does not support native constrained output, but constrained output was requested. Request: %+v", model, input)
			}

			if err := validateVersion(model, info.Versions, input.Config); err != nil {
				return nil, err
			}

			return next(ctx, input, cb)
		}
	}
}

// validateVersion validates that the requested model version is supported.
func validateVersion(model string, versions []string, config any) error {
	var configMap map[string]any

	switch c := config.(type) {
	case map[string]any:
		configMap = c
	default:
		data, err := json.Marshal(config)
		if err != nil {
			return nil
		}
		if err := json.Unmarshal(data, &configMap); err != nil {
			return nil
		}
	}

	versionVal, exists := configMap["version"]
	if !exists {
		return nil
	}

	version, ok := versionVal.(string)
	if !ok {
		return core.NewError(core.INVALID_ARGUMENT, "version must be a string, got %T", versionVal)
	}

	if slices.Contains(versions, version) {
		return nil
	}

	return core.NewError(core.INVALID_ARGUMENT, "model %q does not support version %q, supported versions: %v", model, version, versions)
}

// ContextItemTemplate is the default item template for context augmentation.
func contextItemTemplate(d Document, index int, options *AugmentWithContextOptions) string {
	out := "- "
	if options != nil && options.CitationKey != nil {
		out += fmt.Sprintf("[%v]: ", d.Metadata[*options.CitationKey])
	} else if options == nil || options.CitationKey == nil {
		if ref, ok := d.Metadata["ref"]; ok {
			out += fmt.Sprintf("[%v]: ", ref)
		} else if id, ok := d.Metadata["id"]; ok {
			out += fmt.Sprintf("[%v]: ", id)
		} else {
			out += fmt.Sprintf("[%v]: ", strconv.Itoa(index))
		}
	}
	out += d.concatText() + "\n"
	return out
}

// augmentWithContext augments a request with context documents.
func augmentWithContext(info *ModelInfo, opts *AugmentWithContextOptions) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			// Short-circuiting middleware if context is supported in model.
			if info.Supports.Context {
				return next(ctx, input, cb)
			}
			preface := contextPreface
			if opts != nil && opts.Preface != nil {
				preface = *opts.Preface
			}
			itemTemplate := contextItemTemplate
			if opts != nil && opts.ItemTemplate != nil {
				itemTemplate = opts.ItemTemplate
			}
			// if there is no context in the request, no-op
			if len(input.Docs) == 0 {
				return next(ctx, input, cb)
			}

			userMessage := lastUserMessage(input.Messages)
			// if there are no messages, no-op
			if userMessage == nil {
				return next(ctx, input, cb)
			}

			// if there is already a context part, no-op
			contextPartIndex := -1
			for i, part := range userMessage.Content {
				if part.Metadata != nil && part.Metadata["purpose"] == "context" {
					contextPartIndex = i
					break
				}
			}

			if contextPartIndex >= 0 && userMessage.Content[contextPartIndex].Metadata["pending"] == nil {
				return next(ctx, input, cb)
			}

			out := preface
			for i, doc := range input.Docs {
				out += itemTemplate(*doc, i, opts)
			}
			out += "\n"

			if contextPartIndex >= 0 {
				userMessage.Content[contextPartIndex] = &Part{
					Text:     out,
					Metadata: map[string]any{"purpose": "context"},
				}
			} else {
				userMessage.Content = append(userMessage.Content, &Part{
					Text:     out,
					Metadata: map[string]any{"purpose": "context"},
				})
			}
			return next(ctx, input, cb)
		}
	}
}

// lastUserMessage returns the last user message from a list of messages.
func lastUserMessage(messages []*Message) *Message {
	for i := len(messages) - 1; i >= 0; i-- {
		if messages[i].Role == "user" {
			return messages[i]
		}
	}
	return nil
}

// concatText returns the concatenated text parts of the document content.
func (d *Document) concatText() string {
	var builder strings.Builder
	for _, part := range d.Content {
		if part.IsText() {
			builder.WriteString(part.Text)
		}
	}
	return builder.String()
}

// DownloadRequestMedia downloads media from a URL and replaces the media part with a base64 encoded string.
func DownloadRequestMedia(options *DownloadMediaOptions) ModelMiddleware {
	return func(next ModelFunc) ModelFunc {
		return func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
			client := &http.Client{}
			for _, message := range input.Messages {
				for j, part := range message.Content {
					if !part.IsMedia() || !strings.HasPrefix(part.Text, "http") || (options != nil && options.Filter != nil && !options.Filter(part)) {
						continue
					}

					mediaUrl := part.Text

					resp, err := client.Get(mediaUrl)
					if err != nil {
						return nil, core.NewError(core.INVALID_ARGUMENT, "HTTP error downloading media %q: %v", mediaUrl, err)
					}
					defer resp.Body.Close()

					if resp.StatusCode != http.StatusOK {
						body, _ := io.ReadAll(resp.Body)
						return nil, core.NewError(core.UNKNOWN, "HTTP error downloading media %q: %s", mediaUrl, string(body))
					}

					contentType := part.ContentType
					if contentType == "" {
						contentType = resp.Header.Get("Content-Type")
					}

					var data []byte
					if options != nil && options.MaxBytes > 0 {
						limitedReader := io.LimitReader(resp.Body, int64(options.MaxBytes))
						data, err = io.ReadAll(limitedReader)
					} else {
						data, err = io.ReadAll(resp.Body)
					}
					if err != nil {
						return nil, core.NewError(core.UNKNOWN, "error reading media %q: %v", mediaUrl, err)
					}

					message.Content[j] = NewMediaPart(contentType, fmt.Sprintf("data:%s;base64,%s", contentType, base64.StdEncoding.EncodeToString(data)))
				}
			}
			return next(ctx, input, cb)
		}
	}
}

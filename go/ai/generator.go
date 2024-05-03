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

package ai

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/google/genkit/go/genkit"
)

// Generator is the interface used to query an AI model.
type Generator interface {
	// TODO(randall77): define a type for streaming Generate calls.
	Generate(context.Context, *GenerateRequest, genkit.NoStream) (*GenerateResponse, error)
}

// RegisterGenerator registers the generator in the global registry.
func RegisterGenerator(name string, generator Generator) {
	genkit.RegisterAction(genkit.ActionTypeModel, name,
		genkit.NewStreamingAction(name, generator.Generate))
}

// generatorActionType is the instantiated genkit.Action type registered
// by RegisterGenerator.
// TODO(ianlancetaylor, randall77): add streaming support
type generatorActionType = genkit.Action[*GenerateRequest, *GenerateResponse, struct{}]

// LookupGeneratorAction looks up an action registered by [RegisterGenerator]
// and returns a generator that invokes the action.
func LookupGeneratorAction(name string) (Generator, error) {
	action := genkit.LookupAction(genkit.ActionTypeModel, name, name)
	if action == nil {
		return nil, fmt.Errorf("LookupGeneratorAction: no generator action named %q", name)
	}
	actionInst, ok := action.(*generatorActionType)
	if !ok {
		return nil, fmt.Errorf("LookupGeneratorAction: generator action %q has type %T, want %T", name, action, &generatorActionType{})
	}
	return &generatorAction{actionInst}, nil
}

// generatorAction implements Generator by invoking an action.
type generatorAction struct {
	action *generatorActionType
}

// Generate implements Generator.
func (ga *generatorAction) Generate(ctx context.Context, input *GenerateRequest, cb genkit.NoStream) (*GenerateResponse, error) {
	return ga.action.Run(ctx, input, cb)
}

// Text returns the contents of the first candidate in a
// [GenerateResponse] as a string. It returns an error if there
// are no candidates or if the candidate has no message.
func (gr *GenerateResponse) Text() (string, error) {
	if len(gr.Candidates) == 0 {
		return "", errors.New("no candidates returned")
	}
	msg := gr.Candidates[0].Message
	if msg == nil {
		return "", errors.New("candidate with no message")
	}
	if len(msg.Content) == 0 {
		return "", errors.New("candidate message has no content")
	}
	if len(msg.Content) == 1 {
		return msg.Content[0].Text(), nil
	} else {
		var sb strings.Builder
		for _, p := range msg.Content {
			sb.WriteString(p.Text())
		}
		return sb.String(), nil
	}
}

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

import (
	"context"
)

// Generator is the interface used to query an AI model.
type Generator interface {
	Generate(context.Context, *GenerateRequest) (*GenerateResponse, error)
}

// RegisterGenerator registers the generator in the global registry.
func RegisterGenerator(name string, generator Generator) {
	RegisterAction(ActionTypeModel, name,
		NewAction(name, generator.Generate))
}

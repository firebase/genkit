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

// Package atype provides types for Genkit actions.
package atype

// An ActionType is the kind of an action.
type ActionType string

const (
	ChatLLM          ActionType = "chat-llm"
	TextLLM          ActionType = "text-llm"
	Retriever        ActionType = "retriever"
	Indexer          ActionType = "indexer"
	Embedder         ActionType = "embedder"
	Evaluator        ActionType = "evaluator"
	Flow             ActionType = "flow"
	Model            ActionType = "model"
	Prompt           ActionType = "prompt"
	ExecutablePrompt ActionType = "executable-prompt"
	Tool             ActionType = "tool"
	Util             ActionType = "util"
	Custom           ActionType = "custom"
)

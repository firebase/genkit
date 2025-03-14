// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package atype provides types for Genkit actions.
package atype

// An ActionType is the kind of an action.
type ActionType string

const (
	ChatLLM   ActionType = "chat-llm"
	TextLLM   ActionType = "text-llm"
	Retriever ActionType = "retriever"
	Indexer   ActionType = "indexer"
	Embedder  ActionType = "embedder"
	Evaluator ActionType = "evaluator"
	Flow      ActionType = "flow"
	Model     ActionType = "model"
	Prompt    ActionType = "prompt"
	Tool      ActionType = "tool"
	Util      ActionType = "util"
	Custom    ActionType = "custom"
)

// Copyright 2026 Google LLC
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

// Package tool provides the runtime verbs called from inside a running tool
// function: [Interrupt], [AttachParts], [SendPartial], [SendChunk],
// [ResumeData], and [OriginalInput]. They take a [context.Context], so they
// work in every tool: one written against [ai.ToolContext] (which embeds the
// context) as well as one created with [ai.NewInterruptibleTool].
//
// Everything for building and wiring a tool (constructors and types) lives in
// package [ai], and everything that acts on a value you already hold lives on
// that value: to resolve an interrupted tool request, claim it with
// [ai.InterruptibleToolAction.Interrupted] and use the verbs of the
// [ai.InterruptedCall], or, holding only the part, use [ai.Part.ToToolRestart]
// and [ai.Part.ToToolResponse]. Read the interrupt data itself with
// [ai.InterruptAs].
package tool

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/base"
)

// Interrupt returns the error a tool function returns to pause generation and
// send data to the caller. The interrupted tool request surfaces in
// [ai.ModelResponse.Interrupts]; the caller claims it with
// [ai.InterruptibleToolAction.Interrupted], reads the data with
// [ai.InterruptAs], and restarts the tool with [ai.InterruptedCall.Restart] or
// answers it with [ai.InterruptedCall.Respond]. Middleware returns it from a
// WrapTool hook to hold a tool call without executing it.
//
//	func(ctx context.Context, in TransferInput, resume *Confirmation) (*TransferOutput, error) {
//		if resume == nil {
//			return nil, tool.Interrupt(ctx, TransferInterrupt{Reason: "large_amount", Amount: in.Amount})
//		}
//		...
//	}
//
// ctx is the tool's context, as for the other verbs of this package; nothing
// is read from it today.
//
// data must serialize to a JSON object (a struct or a map): it lands on the
// interrupted tool request as [ai.ToolInterrupt] data, which the wire protocol
// encodes as a JSON object. A value that serializes to a JSON scalar or array
// (e.g. a string, number, or slice) fails the tool call when generation
// records the interrupt; wrap such values in a struct or map field instead.
func Interrupt(ctx context.Context, data any) error {
	return &base.ToolInterruptError{Data: data}
}

// SendPartial streams a partial tool response during tool execution.
// The output is arbitrary structured data (e.g., progress information)
// that will be delivered to the client as a partial [ai.ToolResponse].
//
// This is best-effort: if no streaming callback is available (e.g., the
// tool is called via a non-streaming Generate), the call is a no-op.
// The tool's final return value is always the authoritative response.
//
// Example:
//
//	tool.SendPartial(ctx, map[string]any{"step": "uploading", "progress": 50})
func SendPartial(ctx context.Context, output any) {
	send := base.ToolPartialSenderKey.FromContext(ctx)
	if send == nil {
		return
	}
	send(ctx, output)
}

// SendChunk streams a raw [ai.ModelResponseChunk] during tool execution.
// Unlike [SendPartial], which wraps arbitrary data in a partial tool response,
// SendChunk gives the tool full control over the chunk contents.
//
// This is best-effort: if no streaming callback is available (e.g., the
// tool is called via a non-streaming Generate), the call is a no-op.
// The tool's final return value is always the authoritative response.
func SendChunk(ctx context.Context, chunk *ai.ModelResponseChunk) {
	send := base.ToolChunkSenderKey.FromContext(ctx)
	if send == nil {
		return
	}
	send(ctx, chunk)
}

// AttachParts attaches additional content parts (e.g., media) to the tool's
// response. This can be called from any tool to produce a multipart response
// without changing the function signature. A nil part is ignored, so a
// constructor's failed result can be passed without a check.
//
// Safe for concurrent use from goroutines the tool function spawns; parts are
// appended in call order per goroutine, with no ordering guarantee across
// goroutines.
func AttachParts(ctx context.Context, parts ...*ai.Part) {
	sink := base.ToolPartSinkKey.FromContext(ctx)
	if sink == nil {
		return
	}
	for _, p := range parts {
		if p != nil {
			sink(p)
		}
	}
}

// OriginalInput extracts the typed original input if the caller provided a new
// one when restarting the call (via [ai.InterruptedCall.RestartWithInput] or
// [ai.Part.ToToolRestartWithInput]). Returns the zero value
// and false if no new input was provided, the tool is not being resumed, or the
// type doesn't match.
func OriginalInput[In any](ctx context.Context) (In, bool) {
	v := base.ToolOriginalInputKey.FromContext(ctx)
	if v == nil {
		var zero In
		return zero, false
	}
	return base.ConvertTo[In](v)
}

// ResumeData extracts typed resume data (sent via [ai.InterruptedCall.Restart]
// or [ai.Part.ToToolRestart]) from the context of a restarted tool call.
// Returns the zero value and false if the call is not a resumption or the
// type doesn't match.
//
// Tool functions created with [ai.NewInterruptibleTool] receive the resume
// data as a parameter and don't need this; it is primarily for middleware
// (e.g. a WrapTool hook deciding whether a call was approved on resume) and for
// plain tools resumed by generic callers.
func ResumeData[T any](ctx context.Context) (T, bool) {
	v := base.ToolResumeKey.FromContext(ctx)
	if v == nil {
		var zero T
		return zero, false
	}
	return base.ConvertTo[T](v)
}

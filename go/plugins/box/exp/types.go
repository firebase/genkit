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

package exp

import (
	"context"
	"encoding/json"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
)

// SelfIDEnv is the env var carrying the id of the box a runtime serves.
// Runners set it on every runtime they start, overwriting any inherited value,
// so a nested self-mode runtime can tell "I am this box's runtime" (don't
// re-spawn) from "I manage a different box" (spawn normally).
const SelfIDEnv = "GENKIT_BOX_SELF_ID"

// RunActionRequest is a single runAction call dispatched to a box.
type RunActionRequest struct {
	// Key is the action key in the box, e.g. /tool.v2/runShell, /flow/summarize,
	// /agent/coder.
	Key string `json:"key"`
	// Input is the action input.
	Input json.RawMessage `json:"input,omitempty"`
	// Init is the initialization data for bidi actions such as agents.
	Init json.RawMessage `json:"init,omitempty"`
	// Context is the caller's action context, passed on to the boxed action.
	Context core.ActionContext `json:"context,omitempty"`
	// TelemetryLabels are set as attributes on the box's own span.
	TelemetryLabels map[string]string `json:"telemetryLabels,omitempty"`
}

// RunOptions carries the streaming callbacks of a [Conn.RunAction] call.
// Cancellation is the call's context: cancelling it cancels the boxed action.
type RunOptions struct {
	// OnChunk receives each streamed chunk as the box emits it. When nil the
	// call is not streamed.
	OnChunk func(ctx context.Context, chunk json.RawMessage) error
	// OnTraceID receives the box's trace id as soon as it is known, before the
	// result.
	OnTraceID func(traceID string)
}

// RunActionResult is the result of a [Conn.RunAction] call.
type RunActionResult struct {
	// Result is the action output.
	Result json.RawMessage
	// TraceID is the id of the trace the box recorded for the call.
	TraceID string
}

// Conn is what the box core calls once it has a box. It is deliberately
// narrow: runners do not reimplement reflection, they hand back a connection
// that speaks it.
type Conn interface {
	// RunAction runs one action in the box.
	RunAction(ctx context.Context, req *RunActionRequest, opts *RunOptions) (*RunActionResult, error)
	// ListActions lists the actions the box serves, keyed by action key.
	ListActions(ctx context.Context) (map[string]api.ActionDesc, error)
}

// Runner owns box lifecycle and the routing-key to instance mapping. The
// [Box] decides which key a call goes to (see [Router]) and when a key's box
// is no longer needed (see [WithIdleTimeout]); the runner starts and stops
// whatever backs each key.
type Runner interface {
	// Name identifies the runner kind in logs and errors, e.g. "exec".
	Name() string
	// Acquire returns the box for key, starting it when needed, once it is
	// ready to accept calls. Cancelling ctx stops this caller from waiting; a
	// startup shared with other callers goes on for them.
	Acquire(ctx context.Context, key string) (Conn, error)
	// Release reclaims the box for key. Releasing an unknown key is a no-op.
	Release(ctx context.Context, key string) error
	// Close tears down every box and the runner's own resources.
	Close(ctx context.Context) error
}

// Attacher is implemented by runners that need to know which [Box] owns them.
// Runners that spawn runtimes use the id to set [SelfIDEnv], which is what
// makes self-mode nesting work. [New] calls Attach once.
type Attacher interface {
	Attach(boxID string)
}

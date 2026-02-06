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

package genkit

import (
	aix "github.com/firebase/genkit/go/ai/x"
)

// DefineSessionFlow creates a SessionFlow with automatic snapshot management
// and registers it as a flow action.
//
// A SessionFlow is a stateful, multi-turn conversational flow with automatic
// snapshot persistence and turn semantics. It builds on bidirectional streaming
// to enable ongoing conversations with managed state.
//
// Type parameters:
//   - Stream: Type for status updates sent via the responder
//   - State: Type for user-defined state in snapshots
//
// Example:
//
//	type ChatState struct {
//	    TopicHistory []string `json:"topicHistory,omitempty"`
//	}
//
//	type ChatStatus struct {
//	    Phase string `json:"phase"`
//	}
//
//	chatFlow := genkit.DefineSessionFlow(g, "chatFlow",
//	    func(ctx context.Context, resp aix.Responder[ChatStatus], params *aix.SessionFlowParams[ChatState]) error {
//	        return params.Session.Run(ctx, func(ctx context.Context, input *aix.SessionFlowInput) error {
//	            // ... handle each turn ...
//	            return nil
//	        })
//	    },
//	    aix.WithSnapshotStore(store),
//	)
func DefineSessionFlow[Stream, State any](
	g *Genkit,
	name string,
	fn aix.SessionFlowFunc[Stream, State],
	opts ...aix.SessionFlowOption[State],
) *aix.SessionFlow[Stream, State] {
	return aix.DefineSessionFlow(g.reg, name, fn, opts...)
}

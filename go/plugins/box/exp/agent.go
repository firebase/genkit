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
	"fmt"

	aix "github.com/firebase/genkit/go/ai/exp"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"
	genkitx "github.com/firebase/genkit/go/genkit/exp"
)

// AgentSpec describes a boxed agent the caller cannot inspect: what the Dev
// UI and the caller-side handle need to know.
type AgentSpec struct {
	// Name is the agent's name, both registered here and in the box.
	Name string
	// Description is shown in the Dev UI.
	Description string
	// StateManagement must match the boxed agent: server when it has a
	// session store, client when callers carry the state. Required, because
	// the two take different inits and the boxed agent rejects a mismatch.
	StateManagement aix.AgentStateManagement
	// Abortable says the boxed agent's store supports aborting background
	// work.
	Abortable bool
	// StateSchema is the JSON schema of the agent's custom state, shown in
	// the Dev UI. [SchemaFor] derives one from a Go type.
	StateSchema map[string]any
}

// SchemaFor returns the JSON schema for T, e.g. for [AgentSpec.StateSchema].
func SchemaFor[T any]() map[string]any {
	var zero T
	return core.InferSchemaMap(zero)
}

// DefineAgent registers a boxed agent so it shows up and is chattable in the
// Dev UI like a local one: /agent/<name> plus its agent-snapshot, agent-wait
// and agent-abort companions, all forwarding to the agent in the box. It
// returns the agent's [aix.AgentHandle], which drives the registered action
// in-process, so local and Dev UI calls share one code path and trace shape.
//
//	notes := box.DefineAgent(agentBox, box.AgentSpec{
//		Name:            "notesAgent",
//		StateManagement: aix.AgentStateManagementServer,
//		StateSchema:     box.SchemaFor[NotesState](),
//	})
//	out, err := notes.RunText(ctx, "remember milk", aix.WithSessionID[json.RawMessage](sid))
//
// It returns a handle rather than an [aix.Agent]: an Agent runs its session
// runtime in-process, while this one lives in the box, so the untyped handle
// (custom state as JSON) is the honest surface.
//
// A registered agent has no per-proxy context, so it routes by the session in
// the agent's init ([SessionRoute] reads it), which WithSessionID and the Dev
// UI send. A turn that resumes by snapshot id alone goes to the shared box,
// so give the boxed agent a durable store.
func DefineAgent(b *Box, spec AgentSpec) *aix.AgentHandle {
	if spec.StateManagement != aix.AgentStateManagementServer && spec.StateManagement != aix.AgentStateManagementClient {
		panic(fmt.Sprintf("box.DefineAgent %q: StateManagement must be server or client", spec.Name))
	}
	meta := aix.AgentMetadata{
		StateManagement: spec.StateManagement,
		Abortable:       spec.Abortable,
		StateSchema:     spec.StateSchema,
	}
	return defineBoxedAgent(b, spec.Name, spec.Name, spec.Description, meta)
}

// DefineAgentFrom registers a proxy for a real agent under name (which must
// differ from the agent's own), copying its description and capability
// metadata so the Dev UI renders it like the original. The proxy calls the
// original agent in the box.
func DefineAgentFrom[State any](b *Box, agent *aix.Agent[State], name string) *aix.AgentHandle {
	if name == agent.Name() {
		panic(fmt.Errorf("box.DefineAgentFrom: the proxy must be renamed (got %q, same as the original)", name))
	}
	meta := agent.Handle().Metadata()
	if meta == nil {
		meta = &aix.AgentMetadata{StateManagement: aix.AgentStateManagementClient}
	}
	return defineBoxedAgent(b, name, agent.Name(), agent.Desc().Description, *meta)
}

// defineBoxedAgent registers name's proxy actions for the agent target in the
// box and returns the handle over them.
func defineBoxedAgent(b *Box, name, target, description string, meta aix.AgentMetadata) *aix.AgentHandle {
	t := &boxTransport{b: b, keys: keysFor(target)}
	metadata := map[string]any{"agent": meta, "box": b.id}
	if description != "" {
		metadata["description"] = description
	}
	agent := core.NewBidiActionOf(api.ActionTypeAgent, name, &core.BidiActionOptions{Metadata: metadata},
		func(ctx context.Context, init *aix.AgentInit[json.RawMessage], inCh <-chan *aix.AgentInput, outCh chan<- *aix.AgentStreamChunk) (*aix.AgentOutput[json.RawMessage], error) {
			return runTurns(ctx, t, meta.StateManagement, init, inCh, outCh)
		})
	genkit.RegisterAction(b.g, agent)

	forward := func(atype api.ActionType, key string, input any) {
		// The companions' schemas mirror the agent wire contract.
		genkit.RegisterAction(b.g, core.NewActionOf(atype, name, &core.ActionOptions{
			Metadata:    map[string]any{"box": b.id},
			InputSchema: core.InferSchemaMap(input),
		}, func(ctx context.Context, in json.RawMessage) (json.RawMessage, error) {
			return b.call(ctx, t.req(ctx, key, in, nil), nil)
		}))
	}
	forward(api.ActionTypeAgentSnapshot, t.keys.snapshot, aix.GetSnapshotRequest{})
	forward(api.ActionTypeAgentWait, t.keys.wait, aix.GetSnapshotRequest{})
	if meta.Abortable {
		forward(api.ActionTypeAgentAbort, t.keys.abort, aix.AgentAbortRequest{})
	}
	return genkitx.LookupAgent(b.g, name)
}

// runTurns runs one invocation of the boxed agent. Reflection v1 has no input
// streaming, so each input is one boxed call: a single input (the Dev UI,
// AgentHandle.Run) is exactly one call, and several inputs become one call per
// input, each init threaded from the previous output the way a caller chains
// turns. The loop stops early on a failed or detached turn. With several
// inputs the box records one trace per turn, and the final output carries
// only the last turn's artifacts.
func runTurns(
	ctx context.Context,
	t *boxTransport,
	mgmt aix.AgentStateManagement,
	init *aix.AgentInit[json.RawMessage],
	inCh <-chan *aix.AgentInput,
	outCh chan<- *aix.AgentStreamChunk,
) (*aix.AgentOutput[json.RawMessage], error) {
	forward := func(ctx context.Context, raw json.RawMessage) error {
		var chunk aix.AgentStreamChunk
		if err := json.Unmarshal(raw, &chunk); err != nil {
			return fmt.Errorf("box agent %q: decode chunk: %w", t.keys.name, err)
		}
		select {
		case outCh <- &chunk:
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	}
	var last *aix.AgentOutput[json.RawMessage]
	for input := range inCh {
		out, err := t.Run(ctx, input, init, forward)
		if err != nil {
			return nil, err
		}
		last = out
		if out.FinishReason == aix.AgentFinishReasonFailed || out.FinishReason == aix.AgentFinishReasonDetached {
			break
		}
		init = nextInit(init, out, mgmt)
	}
	if last == nil {
		return &aix.AgentOutput[json.RawMessage]{}, nil
	}
	return last, nil
}

// nextInit is the init for the turn after out: a server-managed agent resumes
// from the new snapshot (keeping the session id, which routing may depend
// on), a client-managed one carries the returned state.
func nextInit(prev *aix.AgentInit[json.RawMessage], out *aix.AgentOutput[json.RawMessage], mgmt aix.AgentStateManagement) *aix.AgentInit[json.RawMessage] {
	if mgmt == aix.AgentStateManagementClient {
		if out.State != nil {
			return &aix.AgentInit[json.RawMessage]{State: out.State}
		}
		return prev
	}
	if out.SnapshotID == "" {
		return prev
	}
	sessionID := out.SessionID
	if sessionID == "" && prev != nil {
		sessionID = prev.SessionID
	}
	return &aix.AgentInit[json.RawMessage]{SnapshotID: out.SnapshotID, SessionID: sessionID}
}

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
)

// agentKeys are the box-side keys of one agent and its companions.
type agentKeys struct {
	name, run, snapshot, wait, abort string
}

func keysFor(name string) agentKeys {
	return agentKeys{
		name:     name,
		run:      actionKey(api.ActionTypeAgent, name),
		snapshot: actionKey(api.ActionTypeAgentSnapshot, name),
		wait:     actionKey(api.ActionTypeAgentWait, name),
		abort:    actionKey(api.ActionTypeAgentAbort, name),
	}
}

// boxTransport is an [aix.AgentTransport] that dispatches each operation to
// the agent in the box: a turn is one runAction on /agent/<name>, a snapshot
// read or wait one on its companion, an abort one on /agent-abort/<name>.
// context is the routing context for every call (see [Agent]).
type boxTransport struct {
	b       *Box
	keys    agentKeys
	context core.ActionContext
}

func (t *boxTransport) req(ctx context.Context, key string, input, init json.RawMessage) *RunActionRequest {
	c := t.context
	if c == nil {
		c = core.FromContext(ctx)
	}
	return &RunActionRequest{Key: key, Input: input, Init: init, Context: c}
}

// Run implements [aix.AgentTransport].
func (t *boxTransport) Run(ctx context.Context, input *aix.AgentInput, init *aix.AgentInit[json.RawMessage], cb func(context.Context, json.RawMessage) error) (*aix.AgentOutput[json.RawMessage], error) {
	in, err := json.Marshal(input)
	if err != nil {
		return nil, fmt.Errorf("box agent %q: marshal input: %w", t.keys.name, err)
	}
	// A fresh session is the empty init, the way JS's own client sends it: a JS
	// agent validates init as an object and rejects a missing one.
	initJSON := json.RawMessage(`{}`)
	if init != nil {
		if initJSON, err = json.Marshal(init); err != nil {
			return nil, fmt.Errorf("box agent %q: marshal init: %w", t.keys.name, err)
		}
	}
	var opts *RunOptions
	if cb != nil {
		opts = &RunOptions{OnChunk: cb}
	}
	res, err := t.b.dispatch(ctx, t.req(ctx, t.keys.run, in, initJSON), opts)
	if err != nil {
		return nil, err
	}
	return decodePtr[aix.AgentOutput[json.RawMessage]](res.Result, t.keys.name, "output")
}

// GetSnapshot implements [aix.AgentTransport].
func (t *boxTransport) GetSnapshot(ctx context.Context, lookup *aix.GetSnapshotRequest) (*aix.SessionSnapshot[json.RawMessage], error) {
	return t.snapshot(ctx, t.keys.snapshot, lookup)
}

// WaitForSnapshot implements [aix.AgentTransport].
func (t *boxTransport) WaitForSnapshot(ctx context.Context, snapshotID string) (*aix.SessionSnapshot[json.RawMessage], error) {
	return t.snapshot(ctx, t.keys.wait, &aix.GetSnapshotRequest{SnapshotID: snapshotID})
}

func (t *boxTransport) snapshot(ctx context.Context, key string, req *aix.GetSnapshotRequest) (*aix.SessionSnapshot[json.RawMessage], error) {
	in, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}
	// A box without the companion answers NOT_FOUND for the action, which
	// the caller reads by status like any other transport's refusal.
	res, err := t.b.dispatch(ctx, t.req(ctx, key, in, nil), nil)
	if err != nil {
		return nil, err
	}
	return decodePtr[aix.SessionSnapshot[json.RawMessage]](res.Result, t.keys.name, "snapshot")
}

// Abort implements [aix.AgentTransport].
func (t *boxTransport) Abort(ctx context.Context, snapshotID string) (aix.SnapshotStatus, error) {
	in, err := json.Marshal(&aix.AgentAbortRequest{SnapshotID: snapshotID})
	if err != nil {
		return "", err
	}
	res, err := t.b.dispatch(ctx, t.req(ctx, t.keys.abort, in, nil), nil)
	if err != nil {
		return "", err
	}
	resp, err := decodePtr[aix.AgentAbortResponse](res.Result, t.keys.name, "abort response")
	if err != nil {
		return "", err
	}
	return resp.Status, nil
}

func decodePtr[T any](raw json.RawMessage, agent, what string) (*T, error) {
	var v T
	if err := json.Unmarshal(raw, &v); err != nil {
		return nil, fmt.Errorf("box agent %q: decode %s: %w", agent, what, err)
	}
	return &v, nil
}

// Agent returns an unregistered handle for the agent named name in the box.
// Every call through it (turns, snapshot reads, aborts) carries actx as its
// action context, which the route sees and the boxed agent receives; nil
// means the caller's context at each call. Handles are cheap, so build one per
// routing context:
//
//	agentBox := box.New(g, runner, box.WithRoute(box.SessionRoute))
//	agent := box.Agent(agentBox, "concierge", core.ActionContext{"sessionId": sid})
//	out, err := agent.RunText(ctx, "hi", aix.WithSessionID[json.RawMessage](sid))
//
// To make the agent visible and chattable in the Dev UI, use [DefineAgent].
func Agent(b *Box, name string, actx core.ActionContext) *aix.AgentHandle {
	return aix.NewAgentHandle(name, nil, &boxTransport{b: b, keys: keysFor(name), context: actx})
}

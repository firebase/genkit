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
	"sync"

	"github.com/firebase/genkit/go/core/api"
)

// fakeCall is one call a fakeRunner served.
type fakeCall struct {
	routeKey string
	req      RunActionRequest
}

// fakeRunner is an in-memory Runner: every key is a "box" that answers with
// handler, so tests can drive routing and leases without processes.
type fakeRunner struct {
	handler func(ctx context.Context, req *RunActionRequest, opts *RunOptions) (any, error)

	mu         sync.Mutex
	attachedTo string
	acquired   []string
	released   []string
	calls      []fakeCall
	closed     bool
	// gate, when set, blocks each RunAction until it is closed.
	gate chan struct{}
}

func newFakeRunner(handler func(ctx context.Context, req *RunActionRequest, opts *RunOptions) (any, error)) *fakeRunner {
	if handler == nil {
		handler = func(_ context.Context, req *RunActionRequest, _ *RunOptions) (any, error) {
			// Echo the input back, wrapped like a tool.v2 envelope for tools.
			var in any
			_ = json.Unmarshal(req.Input, &in)
			if len(req.Key) > 9 && req.Key[:9] == "/tool.v2/" {
				return map[string]any{"output": in}, nil
			}
			return in, nil
		}
	}
	return &fakeRunner{handler: handler}
}

func (r *fakeRunner) Name() string { return "fake" }

func (r *fakeRunner) Attach(boxID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.attachedTo = boxID
}

func (r *fakeRunner) Acquire(_ context.Context, key string) (Conn, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.acquired = append(r.acquired, key)
	return &fakeConn{r: r, key: key}, nil
}

func (r *fakeRunner) Release(_ context.Context, key string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.released = append(r.released, key)
	return nil
}

func (r *fakeRunner) Close(context.Context) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.closed = true
	return nil
}

func (r *fakeRunner) snapshot() (acquired, released []string, calls []fakeCall) {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]string(nil), r.acquired...), append([]string(nil), r.released...), append([]fakeCall(nil), r.calls...)
}

type fakeConn struct {
	r   *fakeRunner
	key string
}

func (c *fakeConn) RunAction(ctx context.Context, req *RunActionRequest, opts *RunOptions) (*RunActionResult, error) {
	c.r.mu.Lock()
	c.r.calls = append(c.r.calls, fakeCall{routeKey: c.key, req: *req})
	gate := c.r.gate
	c.r.mu.Unlock()
	if gate != nil {
		select {
		case <-gate:
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	out, err := c.r.handler(ctx, req, opts)
	if err != nil {
		return nil, err
	}
	raw, err := json.Marshal(out)
	if err != nil {
		return nil, err
	}
	return &RunActionResult{Result: raw, TraceID: "box-trace-" + c.key}, nil
}

func (c *fakeConn) ListActions(context.Context) (map[string]api.ActionDesc, error) {
	return map[string]api.ActionDesc{
		"/tool.v2/shout": {Type: api.ActionTypeToolV2, Key: "/tool.v2/shout", Name: "shout"},
	}, nil
}

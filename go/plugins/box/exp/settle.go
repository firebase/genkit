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
	"sync"
	"time"

	"github.com/firebase/genkit/go/core/api"
)

// defaultSettleTimeout bounds how long a fresh runtime may take to define an
// action after it reports ready.
const defaultSettleTimeout = 10 * time.Second

// settlingConn covers the gap between a runtime reporting ready and it
// defining its actions. A Go runtime registers (v2) or binds its port (v1)
// inside genkit.Init, before the program defines anything, so a call that
// arrives right after readiness can miss an action that is about to exist.
//
// Before the first call to each action key it checks listActions, polling
// until the key appears or the settle deadline (measured from readiness)
// passes; then the call goes through either way, so a key that never appears
// fails with the runtime's own NOT_FOUND. It never inspects the call's error:
// a NOT_FOUND an action returns itself (a missing snapshot) is passed on.
type settlingConn struct {
	Conn
	deadline time.Time

	mu   sync.Mutex
	seen map[string]bool
	// settled is set once the deadline passed or every check succeeded
	// after it; from then on calls skip the check.
	settled bool
}

func newSettlingConn(c Conn, settle time.Duration) *settlingConn {
	return &settlingConn{Conn: c, deadline: time.Now().Add(settle), seen: map[string]bool{}}
}

// RunAction implements [Conn].
func (c *settlingConn) RunAction(ctx context.Context, r *RunActionRequest, opts *RunOptions) (*RunActionResult, error) {
	c.awaitAction(ctx, r.Key)
	return c.Conn.RunAction(ctx, r, opts)
}

func (c *settlingConn) awaitAction(ctx context.Context, key string) {
	c.mu.Lock()
	if c.settled || c.seen[key] {
		c.mu.Unlock()
		return
	}
	c.mu.Unlock()
	for {
		actions, err := c.Conn.ListActions(ctx)
		if err == nil {
			if _, ok := actions[key]; ok {
				c.markSeen(actions)
				return
			}
		}
		if time.Now().After(c.deadline) {
			c.mu.Lock()
			c.settled = true
			c.mu.Unlock()
			return
		}
		select {
		case <-ctx.Done():
			return
		case <-time.After(50 * time.Millisecond):
		}
	}
}

func (c *settlingConn) markSeen(actions map[string]api.ActionDesc) {
	c.mu.Lock()
	defer c.mu.Unlock()
	for k := range actions {
		c.seen[k] = true
	}
}

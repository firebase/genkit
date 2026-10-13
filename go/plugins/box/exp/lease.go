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
	"fmt"
	"sync"
	"time"

	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/status"
)

// Warm starts (or reuses) the box for key and waits until it is ready, e.g.
// at startup to fail fast on a broken build and avoid a cold first call. An
// empty key means [SingletonKey]. The key is used as is (the route is not
// consulted), and the box is subject to the idle timeout like any other, so
// warming is pointless under [PerRequest].
//
// Warm is a no-op in the box's own runtime, so a shared entry point can warm
// at startup without the box starting itself.
func (b *Box) Warm(ctx context.Context, key string) error {
	if b.selfRuntime {
		return nil
	}
	if key == "" {
		key = SingletonKey
	}
	_, done, err := b.acquireKey(ctx, key)
	if err != nil {
		return err
	}
	done()
	return nil
}

// ListActions lists the actions the box for key serves (an empty key means
// [SingletonKey]). It needs a running box, so with a non-singleton route it
// may start one just to answer; prefer knowing what the box exposes on hot
// paths.
func (b *Box) ListActions(ctx context.Context, key string) (map[string]api.ActionDesc, error) {
	if err := b.checkNotSelfRuntime("listed actions"); err != nil {
		return nil, err
	}
	if key == "" {
		key = SingletonKey
	}
	conn, done, err := b.acquireKey(ctx, key)
	if err != nil {
		return nil, err
	}
	defer done()
	return conn.ListActions(ctx)
}

// Close releases every box and closes the runner. Proxies fail after Close.
func (b *Box) Close(ctx context.Context) error {
	b.mu.Lock()
	b.closed = true
	for _, l := range b.leases {
		if l.timer != nil {
			l.timer.Stop()
		}
	}
	b.leases = map[string]*lease{}
	b.mu.Unlock()
	return b.runner.Close(ctx)
}

// dispatch routes req, acquires its box under a lease, and runs it there.
func (b *Box) dispatch(ctx context.Context, req *RunActionRequest, opts *RunOptions) (*RunActionResult, error) {
	if err := b.checkNotSelfRuntime("called a boxed proxy"); err != nil {
		return nil, err
	}
	key, err := b.route.Route(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("box %q: route: %w", b.id, err)
	}
	conn, done, err := b.acquireKey(ctx, key)
	if err != nil {
		return nil, err
	}
	defer done()
	return conn.RunAction(ctx, req, opts)
}

// checkNotSelfRuntime fails in the box's own runtime: in self mode it re-runs
// the caller's program, and reaching the box from there would start a box
// from inside itself.
func (b *Box) checkNotSelfRuntime(what string) error {
	if !b.selfRuntime {
		return nil
	}
	return status.Errorf(status.ErrFailedPrecondition,
		"box %q: %s from within the box's own runtime; use the real (local) action here, or run the box from a separate entry point", b.id, what)
}

// acquireKey acquires the box for key under a lease for exactly one call.
// The returned done ends the lease; calling it more than once is a no-op.
func (b *Box) acquireKey(ctx context.Context, key string) (Conn, func(), error) {
	l, err := b.openLease(key)
	if err != nil {
		return nil, nil, err
	}
	conn, err := b.runner.Acquire(ctx, key)
	if err != nil {
		b.closeLease(key, l)
		return nil, nil, err
	}
	var once sync.Once
	return conn, func() { once.Do(func() { b.closeLease(key, l) }) }, nil
}

func (b *Box) openLease(key string) (*lease, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.closed {
		return nil, status.Errorf(status.ErrFailedPrecondition, "box %q is closed", b.id)
	}
	l := b.leases[key]
	if l == nil {
		l = &lease{}
		b.leases[key] = l
	}
	if l.timer != nil {
		l.timer.Stop()
		l.timer = nil
	}
	l.inflight++
	return l, nil
}

// closeLease ends one call on key. When it was the last one in flight, the
// box is released right away (idle 0) or after the idle timeout; a call
// arriving in the meantime cancels the pending release (see openLease).
func (b *Box) closeLease(key string, l *lease) {
	b.mu.Lock()
	defer b.mu.Unlock()
	l.inflight--
	if l.inflight > 0 || b.idle < 0 || b.closed {
		return
	}
	if b.idle == 0 {
		delete(b.leases, key)
		go b.release(key)
		return
	}
	var t *time.Timer
	t = time.AfterFunc(b.idle, func() {
		b.mu.Lock()
		// A call that arrived before the lock, or a newer timer, supersedes
		// this release.
		if b.leases[key] != l || l.timer != t || l.inflight > 0 {
			b.mu.Unlock()
			return
		}
		delete(b.leases, key)
		b.mu.Unlock()
		b.release(key)
	})
	l.timer = t
}

func (b *Box) release(key string) {
	// A release runs detached from any call, so it gets its own context.
	ctx := context.Background()
	if err := b.runner.Release(ctx, key); err != nil {
		logger.Warn(ctx, "box: release failed", "box", b.id, "key", key, "error", err)
	}
}

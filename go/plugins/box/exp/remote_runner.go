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
)

// RemoteOptions configures [RemoteRunner].
type RemoteOptions struct {
	// URL is the base URL of a runtime serving reflection v1, e.g.
	// http://127.0.0.1:3100.
	URL string
	// Secret is the runtime's reflection secret
	// (GENKIT_REFLECTION_SECRET_TOKEN).
	Secret string
	// Headers are sent with every request, e.g. for a gateway.
	Headers map[string]string
	// ReadyTimeout is how long to wait for the runtime's health check.
	// Defaults to [DefaultReadyTimeout].
	ReadyTimeout time.Duration
}

// remoteReady is one readiness check, shared by every caller waiting on it.
type remoteReady struct {
	done chan struct{}
	err  error
}

type remoteRunner struct {
	opts   RemoteOptions
	client *reflectionClientV1
	conn   Conn

	mu    sync.Mutex
	ready *remoteReady
	ok    bool
}

// RemoteRunner returns a [Runner] over a runtime someone else started: a
// sidecar container, a Cloud Run service, another machine. The runtime is
// started with the same reflection contract as [PodmanRunner] containers
// (GENKIT_REFLECTION_ENABLED=true, GENKIT_REFLECTION_PORT, a matching
// GENKIT_REFLECTION_SECRET_TOKEN).
//
//	b := box.New(g, box.RemoteRunner(box.RemoteOptions{
//		URL:    "http://127.0.0.1:3100",
//		Secret: os.Getenv("BOX_REFLECTION_SECRET"),
//	}))
//
// There is no lifecycle to own, so every routing key maps to the same
// runtime, and Release and Close leave it running. Keys are accepted rather
// than rejected, so a config can use [ExecRunner] locally and RemoteRunner in
// production without changing its route; routes and idle timeouts still run,
// they just start and stop nothing. Readiness is checked once and shared; a
// failed check is not cached, so the next Acquire checks again.
func RemoteRunner(opts RemoteOptions) Runner {
	if opts.URL == "" {
		panic("box.RemoteRunner: URL is required")
	}
	if opts.ReadyTimeout == 0 {
		opts.ReadyTimeout = DefaultReadyTimeout
	}
	client := newReflectionClientV1(opts.URL, opts.Secret, opts.Headers)
	return &remoteRunner{opts: opts, client: client}
}

func (r *remoteRunner) Name() string { return "remote" }

// Acquire implements [Runner]. The readiness check runs detached from any one
// caller's context; each caller only stops waiting when its own ends.
func (r *remoteRunner) Acquire(ctx context.Context, _ string) (Conn, error) {
	r.mu.Lock()
	if r.ok {
		r.mu.Unlock()
		return r.conn, nil
	}
	ready := r.ready
	if ready == nil {
		ready = &remoteReady{done: make(chan struct{})}
		r.ready = ready
		go r.check(ready)
	}
	r.mu.Unlock()
	select {
	case <-ready.done:
		if ready.err != nil {
			return nil, ready.err
		}
		r.mu.Lock()
		defer r.mu.Unlock()
		return r.conn, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

func (r *remoteRunner) check(ready *remoteReady) {
	ready.err = r.client.waitForReady(context.Background(), r.opts.ReadyTimeout)
	r.mu.Lock()
	if ready.err == nil {
		// A runtime started alongside the caller may report ready before it
		// defines its actions; see settlingConn.
		r.conn = newSettlingConn(r.client, defaultSettleTimeout)
		r.ok = true
	} else {
		// Not cached: the runtime may come up later.
		r.ready = nil
	}
	r.mu.Unlock()
	close(ready.done)
}

// Release implements [Runner]. The runtime is not ours to stop.
func (r *remoteRunner) Release(context.Context, string) error { return nil }

// Close implements [Runner]. The runtime is not ours to stop.
func (r *remoteRunner) Close(context.Context) error { return nil }

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
	"fmt"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"github.com/firebase/genkit/go/genkit"
)

// boxOrdinal auto-names boxes created without [WithName].
var boxOrdinal atomic.Int64

// idleUnset marks an idle timeout not set with [WithIdleTimeout]; 0 and
// [NeverRelease] are both meaningful.
const idleUnset time.Duration = -2

// Box runs Genkit actions somewhere other than the current process (a
// subprocess, an OS sandbox, a container, a remote runtime) and hands out
// proxies that call them as if they were local. Where is the [Runner]'s job;
// which box a call goes to is the [Router]'s; how long an idle box lives is
// the idle timeout's.
//
// Create one with [New] and build proxies with the package functions
// ([NewTool], [NewToolFrom], [NewFlow], ...): Go methods cannot take type
// parameters, so the typed constructors take the box as their first argument.
type Box struct {
	id     string
	g      *genkit.Genkit
	runner Runner
	route  Router
	idle   time.Duration
	// selfRuntime is true when this process is itself the runtime of this
	// box (self mode): the box's proxies must not be called from here.
	selfRuntime bool

	mu     sync.Mutex
	leases map[string]*lease
	closed bool
}

// lease tracks the calls in flight on one routing key and its pending
// release.
type lease struct {
	inflight int
	timer    *time.Timer
}

// Option configures a [Box].
type Option func(*Box)

// WithRoute sets the router that picks a box for each call. Defaults to
// [Singleton].
func WithRoute(r Router) Option {
	return func(b *Box) { b.route = r }
}

// WithIdleTimeout sets how long a box may sit idle (no call in flight) before
// it is released. 0 releases it as soon as its last call returns;
// [NeverRelease] keeps it until [Box.Close]. A call arriving in the meantime
// cancels the pending release, and a box is never released mid-call.
//
// Defaults to the route preset's own timeout (never for [Singleton], 0 for
// [PerRequest], [DefaultSessionIdleTimeout] for [SessionRoute]), and to
// [DefaultSessionIdleTimeout] for custom routes.
func WithIdleTimeout(d time.Duration) Option {
	return func(b *Box) { b.idle = d }
}

// WithName sets the box's id. Runners pass it to the runtimes they start
// ([SelfIDEnv]) so a self-mode runtime recognizes its own box. Defaults to a
// construction-order ordinal ("box:0", "box:1", ...), which is stable as long
// as boxes are created deterministically; set a name when they are not.
func WithName(name string) Option {
	return func(b *Box) { b.id = name }
}

// New creates a box that runs actions with runner.
//
//	b := box.New(g, box.ExecRunner(box.Self()), box.WithRoute(box.SessionRoute))
//	defer b.Close(ctx)
//	boxedRunShell := box.NewToolFrom(b, runShell)
func New(g *genkit.Genkit, runner Runner, opts ...Option) *Box {
	if g == nil {
		panic("box.New: nil Genkit")
	}
	if runner == nil {
		panic("box.New: nil Runner")
	}
	b := &Box{g: g, runner: runner, idle: idleUnset, leases: map[string]*lease{}}
	for _, opt := range opts {
		opt(b)
	}
	if b.id == "" {
		b.id = fmt.Sprintf("box:%d", boxOrdinal.Add(1)-1)
	}
	if b.route == nil {
		b.route = Singleton
	}
	if b.idle == idleUnset {
		b.idle = defaultIdleTimeout(b.route)
	}
	b.selfRuntime = os.Getenv(SelfIDEnv) == b.id
	if a, ok := runner.(Attacher); ok {
		a.Attach(b.id)
	}
	return b
}

// ID returns the box's id (see [WithName]).
func (b *Box) ID() string { return b.id }

// Runner returns the box's runner.
func (b *Box) Runner() Runner { return b.runner }

// IsSelfRuntime reports whether this process is the box's own runtime, i.e.
// a self-mode child the runner started. Calling the box's proxies from there
// fails; use the real actions instead.
func (b *Box) IsSelfRuntime() bool { return b.selfRuntime }

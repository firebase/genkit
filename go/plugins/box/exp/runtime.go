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
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

// liveChildren holds every box process this process started, so a box
// runtime that is told to stop can take its own boxes down with it instead of
// orphaning them (nested self mode: agent box -> tool box).
var (
	childrenMu   sync.Mutex
	liveChildren = map[*os.Process]struct{}{}
)

func trackChild(p *os.Process) {
	childrenMu.Lock()
	defer childrenMu.Unlock()
	liveChildren[p] = struct{}{}
}

func untrackChild(p *os.Process) {
	childrenMu.Lock()
	defer childrenMu.Unlock()
	delete(liveChildren, p)
}

// killChildren kills every box this process started.
func killChildren() {
	childrenMu.Lock()
	defer childrenMu.Unlock()
	for p := range liveChildren {
		killGroup(p)
		_ = p.Kill()
	}
}

// parentGone is closed once this process's parent has exited. Linux kills
// a box with its parent anyway (Pdeathsig); this covers macOS and the rest,
// where an orphan is re-parented and its parent pid changes.
func parentGone() <-chan struct{} {
	gone := make(chan struct{})
	parent := os.Getppid()
	go func() {
		for range time.Tick(time.Second) {
			if os.Getppid() != parent {
				close(gone)
				return
			}
		}
	}()
	return gone
}

// IsRuntime reports whether this process is a box runtime: a process a
// runner started to serve a box (it has [SelfIDEnv] set).
func IsRuntime() bool { return os.Getenv(SelfIDEnv) != "" }

// ServeIfRuntime keeps a box runtime alive, and is a no-op otherwise. Call it
// in main after every action is defined, before the program does its own
// work; it returns true when this process is a box runtime, after ctx ends or
// the runner stops the box.
//
//	func main() {
//		ctx := context.Background()
//		g := genkit.Init(ctx)
//		runShell := genkit.DefineTool(g, "runShell", ...)
//		b := box.New(g, box.ExecRunner(box.Self()))
//		boxedRunShell := box.NewToolFrom(b, runShell)
//		if box.ServeIfRuntime(ctx) {
//			return
//		}
//		// The caller's own work, using boxedRunShell.
//	}
//
// In self mode the runner re-runs the whole program, so without this a
// program that does its work and exits (a CLI) would exit in the box too,
// before serving anything. A server that blocks anyway (genkit start, an
// HTTP server) still needs it for the second job: when the runtime is told
// to stop, it stops the boxes it started itself, so nested boxes are never
// orphaned.
func ServeIfRuntime(ctx context.Context) bool {
	if !IsRuntime() {
		return false
	}
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, os.Interrupt, syscall.SIGTERM, syscall.SIGHUP)
	defer signal.Stop(sigs)
	select {
	case <-ctx.Done():
		killChildren()
	case <-parentGone():
		// The host died without stopping us (it crashed or was killed).
		// Nothing will call this box again, and its reflection client would
		// otherwise keep redialing the dead host forever.
		killChildren()
		os.Exit(1)
	case sig := <-sigs:
		killChildren()
		// Exit the way the signal would have (128 + signal number), which
		// supervisors read as "terminated", not "succeeded".
		code := 1
		if s, ok := sig.(syscall.Signal); ok {
			code = 128 + int(s)
		}
		os.Exit(code)
	}
	return true
}

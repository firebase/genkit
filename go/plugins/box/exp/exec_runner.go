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
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/status"
)

// DefaultReadyTimeout is how long a runner waits for a new box to become
// ready, unless [WithReadyTimeout] says otherwise.
const DefaultReadyTimeout = 30 * time.Second

// ExecOption configures an [ExecRunner].
type ExecOption func(*execOptions)

type execOptions struct {
	self         bool
	cmd          []string
	isolate      SandboxProvider
	dir          string
	inherit      InheritEnv
	env          map[string]string
	readyTimeout time.Duration
}

// Self re-runs the current program (os.Executable with os.Args[1:]) as the
// box: one program defines the tools and boxes them, and the copy the runner
// starts serves them. Convenient, at the cost of weaker code isolation than
// a separate entry point. The program must call [ServeIfRuntime] once its
// actions are defined. Mutually exclusive with [Cmd].
func Self() ExecOption { return func(o *execOptions) { o.self = true } }

// Cmd runs a separate entry point as the box, e.g. Cmd("go", "run", "./boxed")
// or a prebuilt binary. It can be any Genkit runtime, in any language, that
// supports reflection v2. Mutually exclusive with [Self].
func Cmd(name string, args ...string) ExecOption {
	return func(o *execOptions) { o.cmd = append([]string{name}, args...) }
}

// WithIsolation runs each box under a [SandboxProvider], e.g. [LocalSandbox].
// Defaults to a plain (trusted) subprocess.
func WithIsolation(p SandboxProvider) ExecOption { return func(o *execOptions) { o.isolate = p } }

// WithDir sets the boxes' working directory. Defaults to the current one.
func WithDir(dir string) ExecOption { return func(o *execOptions) { o.dir = dir } }

// WithInheritEnv sets which of this process's env vars a box inherits:
// [InheritAll] (the default, API keys included) or [InheritBase] (only what
// a runtime needs to start, plus named vars). The box's reflection vars are
// always set by the runner.
func WithInheritEnv(i InheritEnv) ExecOption { return func(o *execOptions) { o.inherit = i } }

// WithEnv sets env vars in the box, on top of what it inherits. The box's own
// reflection vars (GENKIT_REFLECTION_*, GENKIT_RUNTIME_ID) always win.
func WithEnv(env map[string]string) ExecOption { return func(o *execOptions) { o.env = env } }

// WithReadyTimeout sets how long a new box has to connect. Defaults to
// [DefaultReadyTimeout]. A box built on first start (Cmd("go", "run", ...))
// may need more.
func WithReadyTimeout(d time.Duration) ExecOption {
	return func(o *execOptions) { o.readyTimeout = d }
}

// execInstance is one running box.
type execInstance struct {
	runtimeID string
	proc      *process
	conn      Conn
}

// execStart is a startup in flight, shared by every caller of its key.
type execStart struct {
	done chan struct{}
	inst *execInstance
	err  error
}

// ExecRunner runs each box as a local child process that dials back into the
// runner's reflection host (v2). Create one with [ExecRunner].
type execRunner struct {
	opts   execOptions
	secret string

	hostOnce sync.Once
	host     *reflectionHost
	hostErr  error

	mu        sync.Mutex
	boxID     string
	instances map[string]*execInstance
	starting  map[string]*execStart
	closed    bool
}

// ExecRunner returns a [Runner] that starts each box as a local subprocess.
//
//	// Self mode: one program defines the tool and boxes it.
//	b := box.New(g, box.ExecRunner(box.Self()))
//
//	// Separate entry, inheriting only the basics plus one key.
//	box.New(g, box.ExecRunner(box.Cmd("go", "run", "./boxed"),
//		box.WithInheritEnv(box.InheritBase("GEMINI_API_KEY")),
//		box.WithReadyTimeout(2*time.Minute)))
func ExecRunner(opts ...ExecOption) Runner {
	o := execOptions{inherit: InheritAll(), readyTimeout: DefaultReadyTimeout}
	for _, opt := range opts {
		opt(&o)
	}
	switch {
	case o.self && o.cmd != nil:
		panic("box.ExecRunner: Self and Cmd are mutually exclusive")
	case !o.self && o.cmd == nil:
		panic("box.ExecRunner: one of Self or Cmd is required")
	}
	if o.isolate == nil {
		o.isolate = subprocess{}
	}
	return &execRunner{
		opts:      o,
		secret:    newSecret(),
		instances: map[string]*execInstance{},
		starting:  map[string]*execStart{},
	}
}

func (r *execRunner) Name() string { return "exec" }

// Attach implements [Attacher].
func (r *execRunner) Attach(boxID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.boxID = boxID
}

func (r *execRunner) ensureHost() (*reflectionHost, error) {
	r.hostOnce.Do(func() { r.host, r.hostErr = newReflectionHost(r.secret) })
	return r.host, r.hostErr
}

// Acquire implements [Runner]. Concurrent first calls for a key share one
// startup; a caller that gives up stops waiting while the startup goes on for
// the others.
func (r *execRunner) Acquire(ctx context.Context, key string) (Conn, error) {
	host, err := r.ensureHost()
	if err != nil {
		return nil, err
	}
	r.mu.Lock()
	if r.closed {
		r.mu.Unlock()
		return nil, status.Errorf(status.ErrFailedPrecondition, "box exec runner is closed")
	}
	if inst := r.instances[key]; inst != nil && inst.proc.alive() {
		r.mu.Unlock()
		return inst.conn, nil
	}
	s := r.starting[key]
	if s == nil {
		s = &execStart{done: make(chan struct{})}
		r.starting[key] = s
		go r.start(host, key, s)
	}
	r.mu.Unlock()
	select {
	case <-s.done:
		if s.err != nil {
			return nil, s.err
		}
		return s.inst.conn, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// start spawns the box for key and waits until it registers. It runs detached
// from any one caller's context.
func (r *execRunner) start(host *reflectionHost, key string, s *execStart) {
	defer func() {
		r.mu.Lock()
		delete(r.starting, key)
		if s.err == nil {
			if r.closed {
				// Close ran while we started; nobody will stop this box.
				s.err = status.Errorf(status.ErrFailedPrecondition, "box exec runner is closed")
				go s.inst.proc.kill()
			} else {
				r.instances[key] = s.inst
			}
		}
		r.mu.Unlock()
		close(s.done)
	}()

	runtimeID := "box-" + uuid.NewString()
	path, args, err := r.baseCommand()
	if err != nil {
		s.err = err
		return
	}
	r.mu.Lock()
	boxID := r.boxID
	r.mu.Unlock()
	spec, err := r.opts.isolate.Prepare(
		SpawnSpec{Path: path, Args: args, Dir: r.opts.dir},
		ReflectHost{URL: host.url(), Port: host.port()},
	)
	if err != nil {
		s.err = fmt.Errorf("box: %s: %w", r.opts.isolate.Name(), err)
		return
	}
	overrides := map[string]string{
		// Reflection is forced on: a caller running without dev mode, or with
		// its own reflection turned off, still needs working boxes. The URL
		// and secret always win too: under "genkit start" the caller carries
		// the CLI's, which our host would reject.
		reflectionEnabledEnv:  "true",
		reflectionV2ServerEnv: spec.ReflectURL,
		reflectionSecretEnv:   r.secret,
		runtimeIDEnv:          runtimeID,
	}
	if boxID != "" {
		overrides[SelfIDEnv] = boxID
	}
	spec.Env = childEnv(append(os.Environ(), spec.Env...), r.opts.inherit, r.opts.env, overrides)

	logger.Debug(context.Background(), "box: starting runtime", "runtime", runtimeID, "provider", r.opts.isolate.Name(),
		"cmd", strings.Join(append([]string{spec.Path}, spec.Args...), " "))
	proc, err := startProcess(spec.SpawnSpec)
	if err != nil {
		s.err = status.Errorf(status.ErrFailedPrecondition, "box runtime (%s) failed to start: %w", spec.Path, err)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), r.opts.readyTimeout)
	defer cancel()
	ready := make(chan error, 1)
	go func() { ready <- host.waitForRuntime(ctx, runtimeID) }()
	select {
	case err = <-ready:
	case <-proc.exited:
		err = status.Errorf(status.ErrFailedPrecondition, "box runtime (%s) exited before it was ready (%v)", spec.Path, proc.exitErr)
	}
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			err = status.Errorf(status.ErrDeadlineExceeded,
				"timed out after %v waiting for box runtime (%s) to connect; check that it starts, calls genkit.Init, and supports reflection v2 (genkit >= %s)",
				r.opts.readyTimeout, spec.Path, minSecretGenkitVersion)
		}
		proc.kill()
		s.err = err
		return
	}
	s.inst = &execInstance{
		runtimeID: runtimeID,
		proc:      proc,
		conn:      newSettlingConn(host.conn(runtimeID), defaultSettleTimeout),
	}
}

// baseCommand is the program and arguments a box runs, before isolation.
func (r *execRunner) baseCommand() (string, []string, error) {
	if !r.opts.self {
		return r.opts.cmd[0], r.opts.cmd[1:], nil
	}
	exe, err := os.Executable()
	if err != nil {
		return "", nil, fmt.Errorf("box: self mode: locate the current executable: %w", err)
	}
	return exe, os.Args[1:], nil
}

// Release implements [Runner].
func (r *execRunner) Release(_ context.Context, key string) error {
	r.mu.Lock()
	inst := r.instances[key]
	delete(r.instances, key)
	r.mu.Unlock()
	if inst != nil {
		inst.proc.kill()
	}
	return nil
}

// Close implements [Runner].
func (r *execRunner) Close(context.Context) error {
	r.mu.Lock()
	r.closed = true
	insts := make([]*execInstance, 0, len(r.instances))
	for _, inst := range r.instances {
		insts = append(insts, inst)
	}
	r.instances = map[string]*execInstance{}
	r.mu.Unlock()
	var wg sync.WaitGroup
	for _, inst := range insts {
		wg.Add(1)
		go func() {
			defer wg.Done()
			inst.proc.kill()
		}()
	}
	wg.Wait()
	if r.host != nil {
		return r.host.close()
	}
	return nil
}

// process is a started box process.
type process struct {
	cmd *exec.Cmd
	// exited is closed once the process has exited; exitErr is set before.
	exited  chan struct{}
	exitErr error
}

func startProcess(spec SpawnSpec) (*process, error) {
	cmd := exec.Command(spec.Path, spec.Args...)
	cmd.Env = spec.Env
	cmd.Dir = spec.Dir
	cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr
	setProcAttrs(cmd)
	if err := cmd.Start(); err != nil {
		return nil, err
	}
	p := &process{cmd: cmd, exited: make(chan struct{})}
	trackChild(cmd.Process)
	go func() {
		p.exitErr = cmd.Wait()
		untrackChild(cmd.Process)
		close(p.exited)
	}()
	return p, nil
}

func (p *process) alive() bool {
	select {
	case <-p.exited:
		return false
	default:
		return true
	}
}

// kill asks the process to stop, escalates if it lingers, and waits for it.
func (p *process) kill() {
	if !p.alive() {
		return
	}
	terminate(p.cmd.Process)
	select {
	case <-p.exited:
	case <-time.After(3 * time.Second):
		_ = p.cmd.Process.Kill()
		<-p.exited
	}
}

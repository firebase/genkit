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
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime/debug"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"

	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/status"
)

// containerReflectionPort is the port the box's reflection server listens on
// inside the container (GENKIT_REFLECTION_PORT). The container has its own
// network namespace, so a fixed port never collides and needs no discovery.
const containerReflectionPort = 3100

// containerBinary is where a host-built box binary is mounted.
const containerBinary = "/genkit-box/box"

// PodmanMount is a bind mount into the box container.
type PodmanMount struct {
	Source   string
	Target   string
	ReadOnly bool
}

// GoBuild cross-compiles a Go package on the host for the container's
// platform, so the image needs no Go toolchain and a macOS host can box Go
// code into a Linux container. The binary is built once per runner, on first
// use, with CGO_ENABLED=0.
type GoBuild struct {
	// Package is the main package to build, e.g. "./boxed". Empty means the
	// current program (see [PodmanOptions.Self]).
	Package string
	// Dir is the directory the build runs in. Defaults to the project dir.
	Dir string
	// Tags are build tags.
	Tags []string
	// LDFlags are passed as -ldflags.
	LDFlags string
	// Env adds to the build's environment, e.g. GOFLAGS.
	Env []string
}

// PodmanOptions configures [PodmanRunner]. Exactly one of Self, Build or Cmd
// says what the container runs.
type PodmanOptions struct {
	// Image the box runs in, e.g. "alpine:3". Required. With Self or Build it
	// only needs what the boxed tools use (a shell for a shell tool); the Go
	// binary is static.
	Image string
	// Self runs the current program in the container: the runner builds it
	// for linux/<engine arch> and runs it with this process's arguments, so
	// one program can define tools and box them. The program must call
	// [ServeIfRuntime] once its actions are defined.
	Self bool
	// Build cross-compiles a separate entry point for the container.
	Build *GoBuild
	// Cmd runs a command already in the image, e.g. a prebuilt binary or a
	// runtime in another language.
	Cmd []string
	// ProjectDir is mounted into the container at the same absolute path and
	// used as its working directory, so relative paths (prompts/, data)
	// resolve as they do on the host. Defaults to the current directory.
	ProjectDir string
	// NoProjectMount skips the project mount, for a box that needs none.
	NoProjectMount bool
	// Mounts are extra bind mounts.
	Mounts []PodmanMount
	// Bridge gives the box normal network access. By default boxes run on an
	// --internal network: published ports still work, but the box cannot
	// reach the internet.
	Bridge bool
	// NetworkName is the --internal network to create or reuse. Defaults to
	// "genkit-box-internal".
	NetworkName string
	// Env is passed into the box. Containers inherit nothing from this
	// process, so secrets stay out unless listed here.
	Env map[string]string
	// ExtraArgs are raw "podman run" args, e.g. "--memory=512m".
	ExtraArgs []string
	// ReadyTimeout is how long a new container has to answer its health
	// check. Defaults to [DefaultReadyTimeout].
	ReadyTimeout time.Duration
	// Engine is the container engine binary: "podman" (default), "docker",
	// or a path to either.
	Engine string
}

type containerInstance struct {
	name   string
	client *reflectionClientV1
	conn   Conn
}

type containerStart struct {
	done chan struct{}
	inst *containerInstance
	err  error
}

type podmanRunner struct {
	opts       PodmanOptions
	engine     string
	projectDir string

	netMu    sync.Mutex
	netReady bool

	buildMu sync.Mutex
	binary  string // built binary on the host, once built

	mu        sync.Mutex
	boxID     string
	instances map[string]*containerInstance
	starting  map[string]*containerStart
	closed    bool
}

// PodmanRunner returns a [Runner] that runs each box as a podman (or docker)
// container: the first runner with real containment. Egress is blocked by
// default, nothing is inherited from this process, and ExtraArgs can cap
// resources.
//
//	// macOS works too: the runner cross-compiles ./boxed for the engine's VM.
//	b := box.New(g, box.PodmanRunner(box.PodmanOptions{
//		Image:     "alpine:3",
//		Build:     &box.GoBuild{Package: "./boxed"},
//		ExtraArgs: []string{"--memory=512m", "--pids-limit=256"},
//	}))
//
// It speaks reflection v1: the box serves HTTP and the runner publishes the
// port on the host loopback. A v2 dial-back and blocked egress are the same
// route, so they are mutually exclusive.
func PodmanRunner(opts PodmanOptions) Runner {
	modes := 0
	for _, set := range []bool{opts.Self, opts.Build != nil, opts.Cmd != nil} {
		if set {
			modes++
		}
	}
	if modes != 1 {
		panic("box.PodmanRunner: exactly one of Self, Build or Cmd is required")
	}
	if opts.Image == "" {
		panic("box.PodmanRunner: Image is required")
	}
	if opts.ReadyTimeout == 0 {
		opts.ReadyTimeout = DefaultReadyTimeout
	}
	if opts.NetworkName == "" {
		opts.NetworkName = "genkit-box-internal"
	}
	engine := opts.Engine
	if engine == "" {
		engine = "podman"
	}
	dir := opts.ProjectDir
	if dir == "" {
		dir, _ = os.Getwd()
	}
	// The engine binds the real path; on macOS /tmp and /var are symlinks.
	dir = realPath(dir)
	return &podmanRunner{
		opts:       opts,
		engine:     engine,
		projectDir: dir,
		instances:  map[string]*containerInstance{},
		starting:   map[string]*containerStart{},
	}
}

func (r *podmanRunner) Name() string { return "podman" }

// Attach implements [Attacher].
func (r *podmanRunner) Attach(boxID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.boxID = boxID
}

// runEngine runs an engine command to completion.
func (r *podmanRunner) runEngine(ctx context.Context, args ...string) (stdout string, err error) {
	var out, errb bytes.Buffer
	cmd := exec.CommandContext(ctx, r.engine, args...)
	cmd.Stdout, cmd.Stderr = &out, &errb
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("%s %s: %w: %s", r.engine, args[0], err, strings.TrimSpace(errb.String()))
	}
	return strings.TrimSpace(out.String()), nil
}

// ensureNetwork creates the --internal network once. It blocks outbound
// traffic while published ports keep working, which is what gives the box
// egress containment without breaking reflection. A failure is not cached:
// the engine may not have been up yet.
func (r *podmanRunner) ensureNetwork(ctx context.Context) error {
	if r.opts.Bridge {
		return nil
	}
	r.netMu.Lock()
	defer r.netMu.Unlock()
	if r.netReady {
		return nil
	}
	if _, err := r.runEngine(ctx, "network", "inspect", r.opts.NetworkName); err != nil {
		if _, err := r.runEngine(ctx, "network", "create", "--internal", r.opts.NetworkName); err != nil &&
			!strings.Contains(strings.ToLower(err.Error()), "already exists") {
			return status.Errorf(status.ErrFailedPrecondition, "box: create network %q: %w", r.opts.NetworkName, err)
		}
	}
	r.netReady = true
	return nil
}

// engineArch is the engine's Linux architecture as a GOARCH value.
func (r *podmanRunner) engineArch(ctx context.Context) (string, error) {
	format := "{{.Host.Arch}}"
	if filepath.Base(r.engine) == "docker" {
		format = "{{.Architecture}}"
	}
	out, err := r.runEngine(ctx, "info", "--format", format)
	if err != nil {
		return "", status.Errorf(status.ErrUnavailable, "box: is the container engine running? %w", err)
	}
	return goArch(out)
}

// goArch maps an engine's architecture name to GOARCH.
func goArch(engineArch string) (string, error) {
	switch a := strings.TrimSpace(engineArch); a {
	case "amd64", "x86_64":
		return "amd64", nil
	case "arm64", "aarch64":
		return "arm64", nil
	default:
		return "", status.Errorf(status.ErrFailedPrecondition, "box: unsupported container architecture %q", a)
	}
}

// selfPackage is the import path of the running program's main package,
// which is what self mode builds.
func selfPackage() (string, error) {
	info, ok := debug.ReadBuildInfo()
	if !ok || info.Path == "" || info.Path == "command-line-arguments" {
		return "", status.Errorf(status.ErrFailedPrecondition,
			"box: self mode cannot tell which package to build (run it as \"go run .\" or a package path, not \"go run file.go\"), or set Build: &box.GoBuild{Package: ...}")
	}
	return info.Path, nil
}

// goBuildArgs returns the "go build" arguments and environment for b. It is
// pure, so it can be tested without a toolchain.
func goBuildArgs(b GoBuild, goarch, out string) (args, env []string) {
	args = []string{"build", "-o", out, "-trimpath"}
	if len(b.Tags) > 0 {
		args = append(args, "-tags", strings.Join(b.Tags, ","))
	}
	if b.LDFlags != "" {
		args = append(args, "-ldflags", b.LDFlags)
	}
	args = append(args, b.Package)
	env = append([]string{"CGO_ENABLED=0", "GOOS=linux", "GOARCH=" + goarch}, b.Env...)
	return args, env
}

// ensureBinary builds the box binary once, for the engine's architecture,
// into the user cache dir. Go's build cache keeps a rebuild cheap. The build
// does not count against the ready timeout.
func (r *podmanRunner) ensureBinary(ctx context.Context) (string, error) {
	if r.opts.Cmd != nil {
		return "", nil
	}
	r.buildMu.Lock()
	defer r.buildMu.Unlock()
	if r.binary != "" {
		return r.binary, nil
	}
	b := GoBuild{}
	if r.opts.Build != nil {
		b = *r.opts.Build
	}
	if b.Package == "" {
		pkg, err := selfPackage()
		if err != nil {
			return "", err
		}
		b.Package = pkg
	}
	if b.Dir == "" {
		b.Dir = r.projectDir
	}
	goarch, err := r.engineArch(ctx)
	if err != nil {
		return "", err
	}
	cache, err := os.UserCacheDir()
	if err != nil {
		cache = os.TempDir()
	}
	sum := sha256.Sum256([]byte(b.Dir + "\x00" + b.Package + "\x00" + goarch + "\x00" + strings.Join(b.Tags, ",")))
	out := filepath.Join(cache, "genkit-box", hex.EncodeToString(sum[:8]), "box")
	args, env := goBuildArgs(b, goarch, out)
	logger.Debug(ctx, "box: building box binary", "package", b.Package, "goarch", goarch, "out", out)
	cmd := exec.CommandContext(ctx, "go", args...)
	cmd.Dir = b.Dir
	cmd.Env = append(os.Environ(), env...)
	if output, err := cmd.CombinedOutput(); err != nil {
		return "", status.Errorf(status.ErrFailedPrecondition,
			"box: build %s for linux/%s (CGO_ENABLED=0; a cgo program needs a prebuilt image and Cmd): %w\n%s", b.Package, goarch, err, output)
	}
	r.binary = out
	return out, nil
}

// runArgs builds the full "podman run" argv. It is pure and deterministic, so
// it can be tested without an engine.
func (r *podmanRunner) runArgs(name string, hostPort int, secret, binary, boxID string) []string {
	args := []string{
		"run", "--rm", "--init",
		"--name", name,
		// Makes strays discoverable if the host dies without Close:
		//   podman rm -f $(podman ps -aq --filter label=genkit-box)
		"--label", "genkit-box",
		// Loopback only on the host side, on top of the per-container secret.
		"-p", fmt.Sprintf("127.0.0.1:%d:%d", hostPort, containerReflectionPort),
	}
	if !r.opts.Bridge {
		args = append(args, "--network", r.opts.NetworkName)
	}
	if binary != "" {
		args = append(args, "-v", binary+":"+containerBinary+":ro")
	}
	if !r.opts.NoProjectMount {
		args = append(args, "-v", r.projectDir+":"+r.projectDir, "-w", r.projectDir)
	}
	for _, m := range r.opts.Mounts {
		v := realPath(m.Source) + ":" + m.Target
		if m.ReadOnly {
			v += ":ro"
		}
		args = append(args, "-v", v)
	}

	// Containers inherit nothing, so secrets stay out unless passed in Env.
	// GENKIT_REFLECTION_ENABLED turns reflection on without GENKIT_ENV=dev, so
	// the box runs with production defaults. The runner's vars are applied
	// after Env, so a user value cannot break the link.
	env := map[string]string{}
	for k, v := range r.opts.Env {
		env[k] = v
	}
	env[reflectionEnabledEnv] = "true"
	// Published ports arrive on eth0, not loopback.
	env["GENKIT_REFLECTION_HOST"] = "0.0.0.0"
	env["GENKIT_REFLECTION_PORT"] = strconv.Itoa(containerReflectionPort)
	env[reflectionSecretEnv] = secret
	if boxID != "" {
		env[SelfIDEnv] = boxID
	}
	keys := make([]string, 0, len(env))
	for k := range env {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		args = append(args, "-e", k+"="+env[k])
	}

	args = append(args, r.opts.ExtraArgs...)
	args = append(args, r.opts.Image)
	switch {
	case r.opts.Cmd != nil:
		args = append(args, r.opts.Cmd...)
	case r.opts.Self:
		args = append(append(args, containerBinary), os.Args[1:]...)
	default:
		args = append(args, containerBinary)
	}
	return args
}

// freeLoopbackPort picks a free port on the host loopback for publishing.
func freeLoopbackPort() (int, error) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer l.Close()
	return l.Addr().(*net.TCPAddr).Port, nil
}

// Acquire implements [Runner]. Concurrent first calls for a key share one
// startup; a caller that gives up stops waiting while it goes on for others.
func (r *podmanRunner) Acquire(ctx context.Context, key string) (Conn, error) {
	r.mu.Lock()
	if r.closed {
		r.mu.Unlock()
		return nil, status.Errorf(status.ErrFailedPrecondition, "box podman runner is closed")
	}
	if inst := r.instances[key]; inst != nil {
		r.mu.Unlock()
		return inst.conn, nil
	}
	s := r.starting[key]
	if s == nil {
		s = &containerStart{done: make(chan struct{})}
		r.starting[key] = s
		go r.start(key, s)
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

// start runs the container for key and waits until it answers its health
// check. It runs detached from any one caller's context.
func (r *podmanRunner) start(key string, s *containerStart) {
	defer func() {
		r.mu.Lock()
		delete(r.starting, key)
		if s.err == nil {
			if r.closed {
				s.err = status.Errorf(status.ErrFailedPrecondition, "box podman runner is closed")
				go r.stopContainer(s.inst.name)
			} else {
				r.instances[key] = s.inst
			}
		}
		r.mu.Unlock()
		close(s.done)
	}()
	ctx := context.Background()
	if s.err = r.ensureNetwork(ctx); s.err != nil {
		return
	}
	binary, err := r.ensureBinary(ctx)
	if err != nil {
		s.err = err
		return
	}
	hostPort, err := freeLoopbackPort()
	if err != nil {
		s.err = err
		return
	}
	r.mu.Lock()
	boxID := r.boxID
	r.mu.Unlock()
	name := "genkit-box-" + uuid.NewString()[:12]
	secret := newSecret()
	args := r.runArgs(name, hostPort, secret, binary, boxID)
	logger.Debug(ctx, "box: starting container", "name", name,
		"cmd", strings.ReplaceAll(r.engine+" "+strings.Join(args, " "), secret, "<redacted>"))

	// "podman run" stays in the foreground for the container's lifetime, so
	// its exit before readiness means the container failed (bad image, bad
	// command, crash on boot).
	proc, err := startProcess(SpawnSpec{Path: r.engine, Args: args, Env: os.Environ()})
	if err != nil {
		s.err = status.Errorf(status.ErrFailedPrecondition, "box: start %s: %w", r.engine, err)
		return
	}
	client := newReflectionClientV1(fmt.Sprintf("http://127.0.0.1:%d", hostPort), secret, nil)
	readyCtx, cancel := context.WithCancel(ctx)
	defer cancel()
	ready := make(chan error, 1)
	go func() { ready <- client.waitForReady(readyCtx, r.opts.ReadyTimeout) }()
	select {
	case err = <-ready:
	case <-proc.exited:
		err = status.Errorf(status.ErrFailedPrecondition, "box container %s exited before it was ready (%v)", name, proc.exitErr)
	}
	if err != nil {
		r.stopContainer(name)
		proc.kill()
		s.err = err
		return
	}
	s.inst = &containerInstance{
		name:   name,
		client: client,
		conn:   newSettlingConn(client, defaultSettleTimeout),
	}
}

// stopContainer stops a container; --rm removes it once stopped, and a
// force-remove covers a wedged one.
func (r *podmanRunner) stopContainer(name string) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if _, err := r.runEngine(ctx, "stop", "-t", "3", name); err != nil {
		_, _ = r.runEngine(ctx, "rm", "-f", name)
	}
}

// Release implements [Runner].
func (r *podmanRunner) Release(_ context.Context, key string) error {
	r.mu.Lock()
	inst := r.instances[key]
	delete(r.instances, key)
	r.mu.Unlock()
	if inst != nil {
		r.stopContainer(inst.name)
	}
	return nil
}

// Close implements [Runner].
func (r *podmanRunner) Close(context.Context) error {
	r.mu.Lock()
	r.closed = true
	names := make([]string, 0, len(r.instances))
	for _, inst := range r.instances {
		names = append(names, inst.name)
	}
	r.instances = map[string]*containerInstance{}
	r.mu.Unlock()
	var wg sync.WaitGroup
	for _, n := range names {
		wg.Add(1)
		go func() {
			defer wg.Done()
			r.stopContainer(n)
		}()
	}
	wg.Wait()
	return nil
}

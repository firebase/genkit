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
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"slices"
	"strconv"
	"strings"
)

// LocalSandbox returns the OS sandbox for the current platform: seatbelt
// ([SandboxExec]) on macOS, [Bubblewrap] on Linux. It panics elsewhere
// (notably Windows) rather than silently running without isolation; run the
// box in a container there.
//
// These are dev-time guardrails against accidents, not containment for
// hostile code: network egress stays open and there are no resource limits.
// See the package README's isolation levels.
func LocalSandbox() SandboxProvider {
	switch runtime.GOOS {
	case "darwin":
		return SandboxExec(SandboxExecOptions{})
	case "linux":
		return Bubblewrap(BubblewrapOptions{})
	default:
		panic(fmt.Sprintf("box.LocalSandbox: no local sandbox for %s; run the box in a container for isolation on this platform", runtime.GOOS))
	}
}

// SandboxExecOptions configures [SandboxExec].
type SandboxExecOptions struct {
	// Profile is a complete seatbelt profile. When empty, the default denies
	// filesystem writes outside the temp dirs and allows everything else,
	// network included (the box has to reach its host).
	Profile string
	// AllowWrites keeps filesystem writes open in the default profile.
	AllowWrites bool
	// ExtraWritable lists more directories the default profile lets the box
	// write to.
	ExtraWritable []string
}

// SandboxExec returns a macOS seatbelt (sandbox-exec) provider.
//
// The default profile restricts filesystem WRITES only, allowing them under
// /tmp and the user temp dir. Reads are unrestricted, so a boxed tool can
// still read credentials and source, and network egress is open. It guards
// against accidental writes; it is not containment for hostile code.
// sandbox-exec is deprecated by Apple but still ships on current macOS.
func SandboxExec(opts SandboxExecOptions) SandboxProvider { return &sandboxExec{opts: opts} }

type sandboxExec struct{ opts SandboxExecOptions }

func (*sandboxExec) Name() string { return "sandbox-exec" }

func (p *sandboxExec) Prepare(spec SpawnSpec, host ReflectHost) (PreparedSpawn, error) {
	if runtime.GOOS != "darwin" {
		return PreparedSpawn{}, errors.New("the sandbox-exec provider is only available on macOS; use a container runner, or run without isolation")
	}
	out := spec
	out.Path = "sandbox-exec"
	out.Args = append([]string{"-p", p.profile(), spec.Path}, spec.Args...)
	return PreparedSpawn{SpawnSpec: out, ReflectURL: host.URL}, nil
}

// profile is the seatbelt profile the box runs under. It is pure, so it can
// be tested anywhere.
func (p *sandboxExec) profile() string {
	if p.opts.Profile != "" {
		return p.opts.Profile
	}
	lines := []string{"(version 1)", "(allow default)"}
	if !p.opts.AllowWrites {
		// Seatbelt matches real paths (/tmp and /var are symlinks into
		// /private), and Go's temp dir on macOS is per-user under
		// /var/folders, so it needs its own rule. /dev keeps /dev/null and
		// ttys writable.
		writable := []string{"/private/tmp", "/tmp", realPath(os.TempDir()), "/dev"}
		for _, d := range p.opts.ExtraWritable {
			writable = append(writable, realPath(d))
		}
		lines = append(lines, "(deny file-write*)")
		for _, d := range slices.Compact(writable) {
			lines = append(lines, "(allow file-write* (subpath "+strconv.Quote(d)+"))")
		}
	}
	// The reflection dial-back needs loopback network access.
	lines = append(lines, "(allow network*)")
	return strings.Join(lines, "\n")
}

func realPath(p string) string {
	if r, err := filepath.EvalSymlinks(p); err == nil {
		return filepath.Clean(r)
	}
	return filepath.Clean(p)
}

// BubblewrapOptions configures [Bubblewrap].
type BubblewrapOptions struct {
	// ROBind lists read-only bind mounts. Defaults to the system dirs (/usr,
	// /bin, /lib, /lib64, /etc) plus the directory of the box's program, so a
	// self-mode binary (which "go run" builds under /tmp) still runs. The
	// working directory is deliberately not included: keeping your repo out
	// is the point. Setting it replaces the default.
	ROBind []string
	// ExtraROBind adds read-only binds to the default (or to ROBind), e.g.
	// the repo a tool needs to read.
	ExtraROBind []string
	// Tmpfs lists writable, ephemeral mounts. Defaults to /tmp.
	Tmpfs []string
	// UnshareNet isolates the network namespace. It breaks the box's
	// loopback dial-back to its host unless you arrange another path, so
	// leave it off for local boxes.
	UnshareNet bool
	// ExtraArgs are raw bwrap args added before the command.
	ExtraArgs []string
}

// Bubblewrap returns a Linux bubblewrap (bwrap) provider: the box sees a
// read-only system plus a tmpfs /tmp, so your home dir, repo and credentials
// are not present. Network egress stays open (the box dials its host on
// loopback) and there are no CPU, memory or seccomp limits. Stronger than
// [SandboxExec] for the filesystem, but still not containment for hostile
// code.
func Bubblewrap(opts BubblewrapOptions) SandboxProvider { return &bubblewrap{opts: opts} }

type bubblewrap struct{ opts BubblewrapOptions }

func (*bubblewrap) Name() string { return "bubblewrap" }

var systemDirs = []string{"/usr", "/bin", "/lib", "/lib64", "/etc"}

func (p *bubblewrap) Prepare(spec SpawnSpec, host ReflectHost) (PreparedSpawn, error) {
	if runtime.GOOS != "linux" {
		return PreparedSpawn{}, errors.New("the bubblewrap provider is only available on Linux; use a container runner, or run without isolation")
	}
	out := spec
	out.Path = "bwrap"
	out.Args = append(append(p.bwrapArgs(spec.Path), spec.Path), spec.Args...)
	// The box's working directory may not exist inside the sandbox.
	if spec.Dir != "" {
		out.Args = append([]string{"--chdir", spec.Dir}, out.Args...)
	}
	return PreparedSpawn{SpawnSpec: out, ReflectURL: host.URL}, nil
}

// bwrapArgs are the flags before the wrapped command. Pure (no platform
// check), so it can be tested anywhere.
func (p *bubblewrap) bwrapArgs(program string) []string {
	roBind := p.opts.ROBind
	if roBind == nil {
		roBind = slices.Clone(systemDirs)
		if filepath.IsAbs(program) {
			dir := filepath.Dir(program)
			if !slices.ContainsFunc(systemDirs, func(s string) bool { return dir == s || strings.HasPrefix(dir, s+"/") }) {
				roBind = append(roBind, dir)
			}
		}
	}
	roBind = append(roBind, p.opts.ExtraROBind...)
	tmpfs := p.opts.Tmpfs
	if tmpfs == nil {
		tmpfs = []string{"/tmp"}
	}
	args := []string{"--die-with-parent", "--proc", "/proc", "--dev", "/dev"}
	// tmpfs first, so a bind under it (a "go run" binary in /tmp) lands on top.
	for _, d := range tmpfs {
		args = append(args, "--tmpfs", d)
	}
	for _, d := range roBind {
		// -try skips missing paths, so a minimal image doesn't fail the box.
		args = append(args, "--ro-bind-try", d, d)
	}
	if p.opts.UnshareNet {
		args = append(args, "--unshare-net")
	}
	return append(args, p.opts.ExtraArgs...)
}

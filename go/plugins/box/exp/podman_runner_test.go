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
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/firebase/genkit/go/core/status"
)

// argAfter returns the value following flag in args, or "".
func argAfter(args []string, flag string) string {
	if i := slices.Index(args, flag); i >= 0 && i+1 < len(args) {
		return args[i+1]
	}
	return ""
}

// envArgs collects the -e KEY=value pairs of a run argv.
func envArgs(args []string) map[string]string {
	env := map[string]string{}
	for i, a := range args {
		if a == "-e" && i+1 < len(args) {
			k, v, _ := strings.Cut(args[i+1], "=")
			env[k] = v
		}
	}
	return env
}

func TestPodmanRunArgs(t *testing.T) {
	dir := t.TempDir()
	r := PodmanRunner(PodmanOptions{
		Image:      "alpine:3",
		Build:      &GoBuild{Package: "./boxed"},
		ProjectDir: dir,
		Mounts:     []PodmanMount{{Source: dir, Target: "/data", ReadOnly: true}},
		Env:        map[string]string{"GEMINI_API_KEY": "k", reflectionSecretEnv: "user-value"},
		ExtraArgs:  []string{"--memory=512m"},
	}).(*podmanRunner)
	args := r.runArgs("genkit-box-x", 41234, "s3cret", "/cache/box", "tools")
	real := realPath(dir)

	if args[0] != "run" || !slices.Contains(args, "--rm") || argAfter(args, "--label") != "genkit-box" {
		t.Errorf("args = %v, want run --rm with the genkit-box label", args)
	}
	if got := argAfter(args, "-p"); got != "127.0.0.1:41234:3100" {
		t.Errorf("published port = %q, want loopback only", got)
	}
	if got := argAfter(args, "--network"); got != "genkit-box-internal" {
		t.Errorf("network = %q, want the internal network by default", got)
	}
	for _, v := range []string{"/cache/box:" + containerBinary + ":ro", real + ":" + real, real + ":/data:ro"} {
		if !slices.Contains(args, v) {
			t.Errorf("missing mount %s in %v", v, args)
		}
	}
	if argAfter(args, "-w") != real {
		t.Errorf("workdir = %q, want the project dir", argAfter(args, "-w"))
	}
	env := envArgs(args)
	for k, want := range map[string]string{
		"GEMINI_API_KEY":         "k",
		reflectionSecretEnv:      "s3cret", // the runner's own wins
		reflectionEnabledEnv:     "true",
		"GENKIT_REFLECTION_HOST": "0.0.0.0",
		"GENKIT_REFLECTION_PORT": "3100",
		SelfIDEnv:                "tools",
	} {
		if env[k] != want {
			t.Errorf("env %s = %q, want %q", k, env[k], want)
		}
	}
	if _, ok := env["HOME"]; ok {
		t.Error("the container inherited host env")
	}
	tail := args[len(args)-3:]
	if !slices.Equal(tail, []string{"--memory=512m", "alpine:3", containerBinary}) {
		t.Errorf("argv tail = %v, want extra args, image, binary", tail)
	}
}

func TestPodmanRunArgsVariants(t *testing.T) {
	bridge := PodmanRunner(PodmanOptions{Image: "img", Cmd: []string{"node", "boxed.js"}, Bridge: true, NoProjectMount: true}).(*podmanRunner)
	args := bridge.runArgs("n", 1, "s", "", "")
	if slices.Contains(args, "--network") || slices.Contains(args, "-w") {
		t.Errorf("bridge/no-mount args = %v, want no --network and no workdir", args)
	}
	if !slices.Equal(args[len(args)-3:], []string{"img", "node", "boxed.js"}) {
		t.Errorf("Cmd argv tail = %v", args[len(args)-3:])
	}
	if _, ok := envArgs(args)[SelfIDEnv]; ok {
		t.Error("unattached runner set the self id")
	}

	self := PodmanRunner(PodmanOptions{Image: "img", Self: true}).(*podmanRunner)
	args = self.runArgs("n", 1, "s", "/b", "")
	if i := slices.Index(args, containerBinary); i < 0 || !slices.Equal(args[i+1:], os.Args[1:]) {
		t.Errorf("self argv = %v, want the binary with this process's args", args)
	}
}

func TestPodmanRunnerValidates(t *testing.T) {
	for name, opts := range map[string]PodmanOptions{
		"no mode":   {Image: "img"},
		"two modes": {Image: "img", Self: true, Cmd: []string{"x"}},
		"no image":  {Self: true},
	} {
		func() {
			defer func() {
				if recover() == nil {
					t.Errorf("%s: PodmanRunner did not panic", name)
				}
			}()
			PodmanRunner(opts)
		}()
	}
}

func TestGoBuildArgs(t *testing.T) {
	args, env := goBuildArgs(GoBuild{Package: "./boxed", Tags: []string{"a", "b"}, LDFlags: "-s -w", Env: []string{"GOFLAGS=-mod=mod"}}, "arm64", "/out/box")
	if !slices.Equal(args, []string{"build", "-o", "/out/box", "-trimpath", "-tags", "a,b", "-ldflags", "-s -w", "./boxed"}) {
		t.Errorf("args = %v", args)
	}
	if !slices.Equal(env, []string{"CGO_ENABLED=0", "GOOS=linux", "GOARCH=arm64", "GOFLAGS=-mod=mod"}) {
		t.Errorf("env = %v", env)
	}
}

func TestGoArch(t *testing.T) {
	for in, want := range map[string]string{"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64\n": "amd64"} {
		if got, err := goArch(in); err != nil || got != want {
			t.Errorf("goArch(%q) = %q, %v; want %q", in, got, err, want)
		}
	}
	if _, err := goArch("s390x"); err == nil {
		t.Error("goArch(s390x) succeeded")
	}
}

func TestPodmanRunnerEngineFailures(t *testing.T) {
	ctx := context.Background()
	for _, tc := range []struct {
		engine string
		want   status.Name
	}{
		{"failing-engine.sh", status.FailedPrecondition}, // exits before ready
		{"hung-engine.sh", status.DeadlineExceeded},      // never answers
	} {
		t.Run(tc.engine, func(t *testing.T) {
			engine, _ := filepath.Abs(filepath.Join("testdata", tc.engine))
			r := PodmanRunner(PodmanOptions{Image: "img", Cmd: []string{"x"}, Engine: engine, ReadyTimeout: 500 * time.Millisecond})
			t.Cleanup(func() { _ = r.Close(ctx) })
			start := time.Now()
			if _, err := r.Acquire(ctx, "k"); status.Of(err) != tc.want {
				t.Errorf("err = %v, want %s", err, tc.want)
			}
			if d := time.Since(start); d > 10*time.Second {
				t.Errorf("took %v", d)
			}
		})
	}
}

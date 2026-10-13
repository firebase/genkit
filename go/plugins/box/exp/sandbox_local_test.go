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
	"runtime"
	"slices"
	"strings"
	"testing"
)

func TestSandboxExecProfile(t *testing.T) {
	p := &sandboxExec{opts: SandboxExecOptions{ExtraWritable: []string{"/work"}}}
	profile := p.profile()
	for _, want := range []string{"(version 1)", "(deny file-write*)", `(allow file-write* (subpath "/private/tmp"))`, `(subpath "/work")`, "(allow network*)"} {
		if !strings.Contains(profile, want) {
			t.Errorf("profile is missing %s:\n%s", want, profile)
		}
	}
	if open := (&sandboxExec{opts: SandboxExecOptions{AllowWrites: true}}).profile(); strings.Contains(open, "deny") {
		t.Errorf("AllowWrites profile still denies:\n%s", open)
	}
	if custom := (&sandboxExec{opts: SandboxExecOptions{Profile: "(version 1)"}}).profile(); custom != "(version 1)" {
		t.Errorf("custom profile = %q", custom)
	}
}

func TestBubblewrapArgs(t *testing.T) {
	args := (&bubblewrap{}).bwrapArgs("/tmp/go-build123/exe/app")
	joined := strings.Join(args, " ")
	for _, want := range []string{"--die-with-parent", "--ro-bind-try /usr /usr", "--tmpfs /tmp", "--ro-bind-try /tmp/go-build123/exe /tmp/go-build123/exe"} {
		if !strings.Contains(joined, want) {
			t.Errorf("args are missing %q: %s", want, joined)
		}
	}
	// The program's dir is bound after the tmpfs, so it is not hidden by it.
	if slices.Index(args, "--tmpfs") > slices.Index(args, "/tmp/go-build123/exe") {
		t.Errorf("tmpfs mounted after the program dir: %s", joined)
	}
	if strings.Contains(joined, "--unshare-net") {
		t.Error("network unshared by default")
	}

	custom := strings.Join((&bubblewrap{opts: BubblewrapOptions{
		ROBind: []string{"/usr"}, ExtraROBind: []string{"/repo"}, Tmpfs: []string{"/scratch"}, UnshareNet: true,
	}}).bwrapArgs("/usr/bin/app"), " ")
	if strings.Contains(custom, "/etc") || !strings.Contains(custom, "/repo /repo") || !strings.Contains(custom, "--tmpfs /scratch") || !strings.Contains(custom, "--unshare-net") {
		t.Errorf("custom args = %s", custom)
	}
}

func TestLocalSandboxPrepare(t *testing.T) {
	spec := SpawnSpec{Path: "/bin/app", Args: []string{"-x"}, Env: []string{"A=1"}}
	host := ReflectHost{URL: "ws://127.0.0.1:1", Port: 1}
	switch runtime.GOOS {
	case "darwin", "linux":
		out, err := LocalSandbox().Prepare(spec, host)
		if err != nil {
			t.Fatal(err)
		}
		if out.Args[len(out.Args)-2] != "/bin/app" || out.Args[len(out.Args)-1] != "-x" {
			t.Errorf("wrapped args = %v, want the command last", out.Args)
		}
		if !slices.Equal(out.Env, spec.Env) || out.ReflectURL != host.URL {
			t.Errorf("env %v / url %q not passed through", out.Env, out.ReflectURL)
		}
	default:
		defer func() {
			if recover() == nil {
				t.Error("LocalSandbox did not panic on an unsupported platform")
			}
		}()
		LocalSandbox()
	}
	// The other platform's provider refuses to run here.
	other := SandboxProvider(&bubblewrap{})
	if runtime.GOOS == "linux" {
		other = &sandboxExec{}
	}
	if _, err := other.Prepare(spec, host); err == nil {
		t.Errorf("%s prepared on %s", other.Name(), runtime.GOOS)
	}
}

func TestSandboxExecEndToEnd(t *testing.T) {
	if runtime.GOOS != "darwin" {
		t.Skip("sandbox-exec is macOS only")
	}
	ctx := context.Background()
	t.Setenv("BOX_TEST_SECRET", "s3cret")
	b := newSelfBox(t, "sandboxed", []ExecOption{
		WithIsolation(LocalSandbox()),
		WithInheritEnv(InheritBase()),
		WithEnv(map[string]string{"BOX_DEMO": "demo"}),
	})
	write := NewTool[string, string](b, "write", "")

	home, err := os.UserHomeDir()
	if err != nil {
		t.Fatal(err)
	}
	blocked := filepath.Join(home, ".genkit-box-test-should-not-exist")
	t.Cleanup(func() { _ = os.Remove(blocked) })
	if out, err := write.RunRaw(ctx, blocked); err != nil || !strings.Contains(out.(string), "not permitted") {
		t.Errorf("write to $HOME = %v, %v; want operation not permitted", out, err)
	}
	if out, err := write.RunRaw(ctx, filepath.Join(os.TempDir(), "genkit-box-test")); err != nil || out != "ok" {
		t.Errorf("write to the temp dir = %v, %v; want ok", out, err)
	}
	// Env filtering applies inside the sandbox too.
	if _, v := pidOf(t, ctx, b, "BOX_TEST_SECRET"); v != "" {
		t.Errorf("BOX_TEST_SECRET = %q inside the sandbox, want filtered out", v)
	}
	if _, v := pidOf(t, ctx, b, "BOX_DEMO"); v != "demo" {
		t.Errorf("BOX_DEMO = %q inside the sandbox, want demo", v)
	}
}

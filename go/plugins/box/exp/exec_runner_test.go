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
	"encoding/json"
	"fmt"
	"os"
	"slices"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"

	aix "github.com/firebase/genkit/go/ai/exp"
	"github.com/firebase/genkit/go/core/status"
)

// newSelfBox returns a self-mode box over the test binary, closed at cleanup.
func newSelfBox(t *testing.T, name string, runnerOpts []ExecOption, opts ...Option) *Box {
	t.Helper()
	b := New(newTestGenkit(), ExecRunner(append([]ExecOption{Self()}, runnerOpts...)...), append(opts, WithName(name))...)
	t.Cleanup(func() { _ = b.Close(context.Background()) })
	return b
}

// pidOf runs the fixture's pid tool, which reports the runtime pid and the
// value of env var name.
func pidOf(t *testing.T, ctx context.Context, b *Box, name string) (int, string) {
	t.Helper()
	out, err := NewTool[string, string](b, "pid", "").RunRaw(ctx, name)
	if err != nil {
		t.Fatal(err)
	}
	pidStr, val, _ := strings.Cut(out.(string), " ")
	pid, err := strconv.Atoi(pidStr)
	if err != nil {
		t.Fatalf("pid tool returned %q", out)
	}
	return pid, val
}

func TestExecRunnerSelfMode(t *testing.T) {
	ctx := context.Background()
	b := newSelfBox(t, "self", nil)
	if err := b.Warm(ctx, ""); err != nil {
		t.Fatal(err)
	}
	out, err := NewTool[shoutIn, shoutIn](b, "shout", "").RunRaw(ctx, map[string]any{"text": "hi"})
	if err != nil {
		t.Fatal(err)
	}
	if out.(map[string]any)["text"] != "HI" {
		t.Errorf("shout = %v, want HI", out)
	}
	if pid, _ := pidOf(t, ctx, b, ""); pid == os.Getpid() {
		t.Error("the tool ran in the test process, not in the box")
	}

	var chunks []int
	flow := NewStreamingFlow[int, string, countChunk](b, "count")
	for v, err := range flow.Stream(ctx, 2) {
		if err != nil {
			t.Fatal(err)
		}
		if !v.Done {
			chunks = append(chunks, v.Stream.N)
		}
	}
	if !slices.Equal(chunks, []int{1, 2}) {
		t.Errorf("chunks = %v, want [1 2]", chunks)
	}

	actions, err := b.ListActions(ctx, "")
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := actions["/tool.v2/shout"]; !ok {
		t.Error("ListActions is missing /tool.v2/shout")
	}
}

func TestExecRunnerPerRequest(t *testing.T) {
	ctx := context.Background()
	b := newSelfBox(t, "perRequest", nil, WithRoute(PerRequest))
	p1, _ := pidOf(t, ctx, b, "")
	p2, _ := pidOf(t, ctx, b, "")
	if p1 == p2 {
		t.Errorf("perRequest reused box process %d", p1)
	}
}

func TestExecRunnerSharesConcurrentStartup(t *testing.T) {
	ctx := context.Background()
	r := ExecRunner(Self())
	b := New(newTestGenkit(), r, WithName("shared"))
	t.Cleanup(func() { _ = b.Close(ctx) })

	// One caller gives up right away; the others must still get the box.
	quitter, cancel := context.WithCancel(ctx)
	cancel()
	if _, err := r.Acquire(quitter, SingletonKey); err == nil {
		t.Error("Acquire with a cancelled context succeeded")
	}

	var wg sync.WaitGroup
	pids := make([]int, 3)
	for i := range pids {
		wg.Add(1)
		go func() {
			defer wg.Done()
			pids[i], _ = pidOf(t, ctx, b, "")
		}()
	}
	wg.Wait()
	if pids[0] != pids[1] || pids[1] != pids[2] {
		t.Errorf("concurrent first calls got pids %v, want one shared box", pids)
	}
}

func TestExecRunnerStartupFailures(t *testing.T) {
	ctx := context.Background()
	for _, tc := range []struct {
		name   string
		runner Runner
		want   status.Name
	}{
		{"missing binary", ExecRunner(Cmd("/nonexistent/box-entry")), status.FailedPrecondition},
		{"exits early", ExecRunner(Cmd("sh", "-c", "exit 3")), status.FailedPrecondition},
		{"never connects", ExecRunner(Cmd("sleep", "30"), WithReadyTimeout(300*time.Millisecond)), status.DeadlineExceeded},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Cleanup(func() { _ = tc.runner.Close(ctx) })
			start := time.Now()
			_, err := tc.runner.Acquire(ctx, "k")
			if status.Of(err) != tc.want {
				t.Errorf("err = %v, want %s", err, tc.want)
			}
			if time.Since(start) > 5*time.Second {
				t.Errorf("took %v, want a fast failure", time.Since(start))
			}
		})
	}
}

func TestExecRunnerEnv(t *testing.T) {
	ctx := context.Background()
	t.Setenv("BOX_TEST_SECRET", "s3cret")
	t.Setenv("BOX_TEST_ALLOWED", "allowed")

	t.Run("inherits everything by default", func(t *testing.T) {
		b := newSelfBox(t, "envAll", nil)
		if _, v := pidOf(t, ctx, b, "BOX_TEST_SECRET"); v != "s3cret" {
			t.Errorf("BOX_TEST_SECRET = %q, want inherited", v)
		}
	})
	t.Run("InheritBase keeps secrets out but sets env", func(t *testing.T) {
		b := newSelfBox(t, "envBase", []ExecOption{
			WithInheritEnv(InheritBase("BOX_TEST_ALLOWED")),
			WithEnv(map[string]string{"BOX_DEMO": "set by the host"}),
		})
		for name, want := range map[string]string{
			"BOX_TEST_SECRET":  "",
			"BOX_TEST_ALLOWED": "allowed",
			"BOX_DEMO":         "set by the host",
		} {
			if _, v := pidOf(t, ctx, b, name); v != want {
				t.Errorf("%s = %q, want %q", name, v, want)
			}
		}
	})
}

func TestExecRunnerOverridesInheritedReflectionSettings(t *testing.T) {
	// Under "genkit start" the caller carries the CLI's secret and v2 URL,
	// and may have turned its own reflection off; the box must still connect
	// to the runner's host.
	t.Setenv(reflectionSecretEnv, "the-cli-secret")
	t.Setenv(reflectionV2ServerEnv, "ws://127.0.0.1:1")
	t.Setenv(reflectionEnabledEnv, "false")
	b := newSelfBox(t, "override", []ExecOption{WithEnv(map[string]string{reflectionSecretEnv: "user-value"})})
	if err := b.Warm(context.Background(), ""); err != nil {
		t.Fatalf("box with inherited reflection settings did not start: %v", err)
	}
}

func TestChildEnv(t *testing.T) {
	parent := []string{"PATH=/bin", "HOME=/home/me", "GOCACHE=/c", "API_KEY=k", "OTHER=o", "LC_ALL=C"}
	get := func(env []string) map[string]string {
		m := map[string]string{}
		for _, kv := range env {
			k, v, _ := strings.Cut(kv, "=")
			m[k] = v
		}
		return m
	}
	all := get(childEnv(parent, InheritAll(), nil, nil))
	if all["API_KEY"] != "k" || all["OTHER"] != "o" {
		t.Errorf("InheritAll = %v, want everything", all)
	}
	base := get(childEnv(parent, InheritBase("API_KEY"), nil, nil))
	if base["API_KEY"] != "k" || base["PATH"] != "/bin" || base["GOCACHE"] != "/c" || base["LC_ALL"] != "C" {
		t.Errorf("InheritBase = %v, want the basics plus API_KEY", base)
	}
	if _, ok := base["OTHER"]; ok {
		t.Errorf("InheritBase leaked OTHER: %v", base)
	}
	layered := get(childEnv(parent, InheritAll(), map[string]string{"OTHER": "env", "X": "env"}, map[string]string{"X": "override"}))
	if layered["OTHER"] != "env" || layered["X"] != "override" {
		t.Errorf("precedence = %v, want env over inherited and overrides over env", layered)
	}
}

func TestExecRunnerNestsSelfModeBoxes(t *testing.T) {
	ctx := context.Background()
	// The test process boxes the agentBox; its runtime boxes the toolBox.
	b := newSelfBox(t, "agentBox", nil)
	out, err := NewFlow[string, string](b, "nested").Run(ctx, "")
	if err != nil {
		t.Fatal(err)
	}
	var mid, inner int
	if _, err := fmt.Sscanf(out, "%d>%d", &mid, &inner); err != nil {
		t.Fatalf("nested = %q: %v", out, err)
	}
	if mid == os.Getpid() || inner == mid || inner == os.Getpid() {
		t.Errorf("pids test=%d agentBox=%d toolBox=%d, want three processes", os.Getpid(), mid, inner)
	}

	// Stopping the agentBox stops the toolBox it started.
	if err := b.Close(ctx); err != nil {
		t.Fatal(err)
	}
	waitFor(t, func() bool { return !processAlive(inner) })
}

func TestExecRunnerBoxedAgent(t *testing.T) {
	ctx := context.Background()
	t.Setenv("BOX_TEST_STORE", t.TempDir())

	t.Run("turns resume in the box", func(t *testing.T) {
		b := newSelfBox(t, "agentSingleton", nil)
		notes := DefineAgent(b, AgentSpec{Name: "notes", StateManagement: aix.AgentStateManagementServer})
		first, err := notes.RunText(ctx, "milk", aix.WithSessionID[json.RawMessage]("s-single"))
		if err != nil {
			t.Fatal(err)
		}
		second, err := notes.RunText(ctx, "eggs", aix.WithSessionID[json.RawMessage]("s-single"))
		if err != nil {
			t.Fatal(err)
		}
		if !strings.HasSuffix(first.Message.Text(), ":milk") || !strings.HasSuffix(second.Message.Text(), ":milk,eggs") {
			t.Errorf("replies %q, %q; want the notes to accumulate", first.Message.Text(), second.Message.Text())
		}
		snap, err := notes.GetSnapshot(ctx, second.SnapshotID)
		if err != nil || snap.SnapshotID != second.SnapshotID {
			t.Errorf("GetSnapshot = %+v, %v", snap, err)
		}
	})

	t.Run("a shared store continues a session on another box", func(t *testing.T) {
		b := newSelfBox(t, "agentPerRequest", nil, WithRoute(PerRequest))
		notes := DefineAgent(b, AgentSpec{Name: "notes", StateManagement: aix.AgentStateManagementServer})
		first, err := notes.RunText(ctx, "a", aix.WithSessionID[json.RawMessage]("s-moved"))
		if err != nil {
			t.Fatal(err)
		}
		second, err := notes.RunText(ctx, "b", aix.WithSessionID[json.RawMessage]("s-moved"))
		if err != nil {
			t.Fatal(err)
		}
		p1, _, _ := strings.Cut(first.Message.Text(), ":")
		p2, notes2, _ := strings.Cut(second.Message.Text(), ":")
		if p1 == p2 {
			t.Errorf("both turns ran in box %s, want two", p1)
		}
		if notes2 != "a,b" {
			t.Errorf("second box saw notes %q, want a,b from the shared store", notes2)
		}
	})
}

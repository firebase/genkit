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
	"os"
	"os/exec"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	aix "github.com/firebase/genkit/go/ai/exp"
	"github.com/firebase/genkit/go/ai/exp/localstore"
	"github.com/firebase/genkit/go/ai/tool"
	"github.com/firebase/genkit/go/core/status"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/genkitbridge"
)

// fixtureEnv makes the test binary run as a Genkit runtime instead of the
// tests: each subprocess test starts os.Args[0] with it set. The runtime
// takes its reflection settings (v1 port or v2 server, secret) from the
// usual GENKIT_REFLECTION_* env vars.
const fixtureEnv = "BOX_TEST_FIXTURE"

func TestMain(m *testing.M) {
	// A self-mode box re-runs the test binary with the test flags; IsRuntime
	// tells it apart from the test run.
	if os.Getenv(fixtureEnv) != "" || IsRuntime() {
		runFixture()
		return
	}
	os.Exit(m.Run())
}

// runFixture serves the fixture actions until the process is stopped, the
// way a self-mode program would.
func runFixture() {
	ctx := context.Background()
	g := genkit.Init(ctx)
	defineFixtureActions(g)
	defineNestedFixture(g)
	defineStoredAgentFixture(g)
	if !ServeIfRuntime(ctx) {
		select {} // a plain v1/v2 runtime: the test kills it
	}
}

// defineNestedFixture is the middle level of the nesting test: the "nested"
// flow runs in an agentBox runtime and calls the pid tool in a toolBox the
// runtime starts itself, reporting both pids.
func defineStoredAgentFixture(g *genkit.Genkit) {
	dir := os.Getenv("BOX_TEST_STORE")
	if dir == "" {
		return
	}
	store, err := localstore.NewFileSessionStore[noteState](dir)
	if err != nil {
		panic(err)
	}
	// A model-free agent: each turn appends the user's text to the notes in
	// custom state and answers with the pid and every note so far.
	aix.DefineCustomAgent(genkitbridge.RegistryOf(g), "notes",
		func(ctx context.Context, resp aix.Responder, sess *aix.SessionRunner[noteState]) (*aix.AgentResult, error) {
			if err := sess.Run(ctx, func(ctx context.Context, in *aix.AgentInput) (*aix.TurnResult, error) {
				sess.UpdateCustom(func(s noteState) noteState {
					s.Notes = append(s.Notes, in.Message.Text())
					return s
				})
				reply := fmt.Sprintf("%d:%s", os.Getpid(), strings.Join(sess.Custom().Notes, ","))
				sess.AddMessages(ai.NewModelTextMessage(reply))
				return &aix.TurnResult{}, nil
			}); err != nil {
				return nil, err
			}
			return sess.Result(), nil
		},
		aix.WithSessionStore(store),
	)
}

type noteState struct {
	Notes []string `json:"notes"`
}

func defineNestedFixture(g *genkit.Genkit) {
	toolBox := New(g, ExecRunner(Self()), WithName("toolBox"))
	pid := NewTool[string, string](toolBox, "pid", "")
	genkit.DefineFlow(g, "nested", func(ctx context.Context, _ string) (string, error) {
		inner, err := pid.RunRaw(ctx, "")
		if err != nil {
			return "", err
		}
		return fmt.Sprintf("%d>%v", os.Getpid(), inner), nil
	})
}

// defineFixtureActions registers what the subprocess tests call.
func defineFixtureActions(g *genkit.Genkit) {
	genkit.DefineTool(g, "shout", "Shouts.", func(_ *ai.ToolContext, in shoutIn) (shoutIn, error) {
		return shoutIn{Text: strings.ToUpper(in.Text)}, nil
	})
	genkit.DefineTool(g, "draw", "Draws.", func(tc *ai.ToolContext, in shoutIn) (string, error) {
		tool.AttachParts(tc, ai.NewMediaPart("image/png", "data:image/png;base64,AAAA"))
		return "drew " + in.Text, nil
	})
	genkit.DefineTool(g, "pid", "Reports the runtime pid and env.", func(_ *ai.ToolContext, name string) (string, error) {
		return fmt.Sprintf("%d %s", os.Getpid(), os.Getenv(name)), nil
	})
	genkit.DefineTool(g, "write", "Writes a file and reports the error, if any.", func(_ *ai.ToolContext, path string) (string, error) {
		if err := os.WriteFile(path, []byte("x"), 0o600); err != nil {
			return err.Error(), nil
		}
		_ = os.Remove(path)
		return "ok", nil
	})
	genkit.DefineStreamingFlow(g, "count", func(ctx context.Context, n int, cb func(context.Context, countChunk) error) (string, error) {
		for i := 1; i <= n; i++ {
			if cb != nil {
				if err := cb(ctx, countChunk{N: i}); err != nil {
					return "", err
				}
			}
		}
		return fmt.Sprintf("counted %d", n), nil
	})
	genkit.DefineFlow(g, "fail", func(context.Context, string) (string, error) {
		return "", status.Errorf(status.ErrInvalidArgument, "bad input")
	})
	genkit.DefineFlow(g, "block", func(ctx context.Context, _ string) (string, error) {
		<-ctx.Done()
		return "", ctx.Err()
	})
}

// startFixture starts the test binary as a runtime with env added to the
// current environment, and kills it at test cleanup.
func startFixture(t *testing.T, env ...string) *exec.Cmd {
	t.Helper()
	cmd := exec.Command(os.Args[0])
	cmd.Env = append(os.Environ(), append([]string{fixtureEnv + "=1"}, env...)...)
	cmd.Stdout, cmd.Stderr = os.Stderr, os.Stderr
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
	})
	return cmd
}

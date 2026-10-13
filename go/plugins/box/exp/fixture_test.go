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
	"github.com/firebase/genkit/go/ai/tool"
	"github.com/firebase/genkit/go/core/status"
	"github.com/firebase/genkit/go/genkit"
)

// fixtureEnv makes the test binary run as a Genkit runtime instead of the
// tests: each subprocess test starts os.Args[0] with it set. The runtime
// takes its reflection settings (v1 port or v2 server, secret) from the
// usual GENKIT_REFLECTION_* env vars.
const fixtureEnv = "BOX_TEST_FIXTURE"

func TestMain(m *testing.M) {
	if os.Getenv(fixtureEnv) != "" {
		runFixture()
		return
	}
	os.Exit(m.Run())
}

// runFixture serves the fixture actions until the process is killed.
func runFixture() {
	ctx := context.Background()
	g := genkit.Init(ctx)
	defineFixtureActions(g)
	<-ctx.Done() // never: the parent kills the process
	select {}
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

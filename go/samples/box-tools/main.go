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

// This sample is Genkit in a Box in self mode: one program defines a runShell
// tool and boxes it in a local OS sandbox (seatbelt on macOS, bubblewrap on
// Linux), so every call runs jailed in a separate process. The agent and the
// Gemini API key stay in this process; only runShell calls cross over.
//
// The runner re-runs this same program as the box (box.Self()). The box
// inherits none of this process's env beyond the basics (InheritBase), so
// GEMINI_API_KEY stays out of it, and box.IsRuntime tells the copy apart so
// it skips the model plugin it has no key for.
//
// Run it with the Dev UI:
//
//	curl -sL cli.genkit.dev | bash    # install the Genkit CLI, once
//	export GEMINI_API_KEY=...
//	genkit start -- go run .
//
// Then call the runInBox flow with {"cmd": "echo $$"}: the pid is the box's,
// not this process's. Call it with {"cmd": "echo key=$GEMINI_API_KEY demo=$BOX_DEMO"}:
// the key is empty and BOX_DEMO is what the host passed in. Chat with
// codingAgent, and open a trace: the runShell span is marked as boxed, and
// box:traceId links it to the box's own trace.
//
// What the sandbox blocks: on macOS {"cmd": "echo hi > ~/nope.txt"} fails with
// "Operation not permitted" while {"cmd": "echo hi > /tmp/ok.txt && cat /tmp/ok.txt"}
// works. On Linux {"cmd": "ls ~"} fails: your home dir is not mounted.
package main

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	box "github.com/firebase/genkit/go/plugins/box/exp"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

type ShellInput struct {
	Cmd string `json:"cmd" jsonschema_description:"The shell command to run."`
}

type ShellOutput struct {
	Stdout string `json:"stdout,omitempty"`
	Error  string `json:"error,omitempty"`
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// The box runs only runShell, so it needs no model plugin, and has no key
	// for one anyway.
	var opts []genkit.GenkitOption
	if !box.IsRuntime() {
		opts = append(opts, genkit.WithPlugins(&googlegenai.GoogleAI{}))
	}
	g := genkit.Init(ctx, opts...)

	// The real tool. Its body runs in the box process.
	runShell := genkit.DefineTool(g, "runShell", "Run a shell command and return its stdout.",
		func(tc *ai.ToolContext, in ShellInput) (ShellOutput, error) {
			ctx, cancel := context.WithTimeout(tc, 10*time.Second)
			defer cancel()
			out, err := exec.CommandContext(ctx, "sh", "-c", in.Cmd).Output()
			if err != nil {
				// Report failures to the model rather than failing the call.
				msg := err.Error()
				if ee, ok := err.(*exec.ExitError); ok && len(ee.Stderr) > 0 {
					msg += ": " + strings.TrimSpace(string(ee.Stderr))
				}
				return ShellOutput{Stdout: strings.TrimSpace(string(out)), Error: msg}, nil
			}
			return ShellOutput{Stdout: strings.TrimSpace(string(out))}, nil
		})

	myBox := box.New(g, box.ExecRunner(
		box.Self(),
		box.WithIsolation(box.LocalSandbox()),
		box.WithInheritEnv(box.InheritBase()),
		box.WithEnv(map[string]string{"BOX_DEMO": "set by the host"}),
	))
	defer myBox.Close(context.Background())

	// A boxed handle to the tool: same name and schemas, no restatement.
	boxedRunShell := box.NewToolFrom(myBox, runShell)

	// In the box's own process, serve runShell and stop here.
	if box.ServeIfRuntime(ctx) {
		return
	}

	// Start the box now rather than on the first tool call.
	if err := myBox.Warm(ctx, ""); err != nil {
		panic(err)
	}

	// The model call (and the key) live here; only runShell crosses over.
	genkit.DefineFlow(g, "codingAgent", func(ctx context.Context, question string) (string, error) {
		return genkit.GenerateText(ctx, g,
			ai.WithModelName("googleai/gemini-flash-latest"),
			ai.WithSystem("You are a helpful coding assistant. Use runShell to inspect the system when needed. Keep answers concise."),
			ai.WithPrompt(question),
			ai.WithTools(boxedRunShell),
		)
	})

	// Exercises the boxed tool directly, without the model.
	genkit.DefineFlow(g, "runInBox", func(ctx context.Context, in ShellInput) (ShellOutput, error) {
		var out ShellOutput
		// RunRaw reports the output in its JSON form; decode it back.
		raw, err := boxedRunShell.RunRaw(ctx, in)
		if err != nil {
			return out, err
		}
		b, err := json.Marshal(raw)
		if err != nil {
			return out, err
		}
		err = json.Unmarshal(b, &out)
		return out, err
	})

	// Serve the Dev UI until interrupted; the deferred Close stops the box.
	<-ctx.Done()
}

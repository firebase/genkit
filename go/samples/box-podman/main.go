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

// This sample runs a shell tool in a podman (or docker) container: real
// containment, unlike the local sandboxes. The model call and the Gemini API
// key stay in this process; the tool runs in ./boxed, cross-compiled on the
// host for the container's Linux VM, so it works from macOS with no Go
// toolchain in the image and no Containerfile.
//
// In the box: no host env (GEMINI_API_KEY is absent), no host filesystem
// beyond the project dir, no internet (an --internal network), and capped
// memory and pids.
//
// Run it (podman machine start, once, on macOS):
//
//	export GEMINI_API_KEY=...
//	genkit start -- go run .
//
// Then call runInBox with {"cmd": "uname -a"} (Linux), {"cmd": "printenv GEMINI_API_KEY"}
// (empty) and {"cmd": "wget -qO- https://example.com"} (fails: no egress), or
// ask codingAgent about the system it can see.
package main

import (
	"context"
	"encoding/json"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	box "github.com/firebase/genkit/go/plugins/box/exp"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

// ShellInput and ShellOutput declare the boxed tool's shape: the tool lives
// only in ./boxed, so this side states what it needs to call it.
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

	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	podmanBox := box.New(g, box.PodmanRunner(box.PodmanOptions{
		// Any image with a shell; the boxed binary is static.
		Image: "docker.io/library/alpine:3",
		Build: &box.GoBuild{Package: "./boxed"},
		// Containers inherit nothing; pass only what the box needs.
		Env:       map[string]string{"BOX_DEMO": "set by the host"},
		ExtraArgs: []string{"--memory=256m", "--pids-limit=128"},
		// The first start builds ./boxed.
		ReadyTimeout: 2 * time.Minute,
	}))
	defer podmanBox.Close(context.Background())

	runShell := box.DefineTool[ShellInput, ShellOutput](podmanBox, "runShell",
		"Run a shell command in an isolated Linux container and return its output.")

	// Build and start the container now rather than on the first call.
	if err := podmanBox.Warm(ctx, ""); err != nil {
		panic(err)
	}

	genkit.DefineFlow(g, "codingAgent", func(ctx context.Context, question string) (string, error) {
		return genkit.GenerateText(ctx, g,
			ai.WithModelName("googleai/gemini-flash-latest"),
			ai.WithSystem("You are a helpful assistant with a Linux sandbox. Use runShell to answer questions about it. Keep answers concise."),
			ai.WithPrompt(question),
			ai.WithTools(runShell),
		)
	})

	// Exercises the boxed tool directly, without the model.
	genkit.DefineFlow(g, "runInBox", func(ctx context.Context, in ShellInput) (ShellOutput, error) {
		var out ShellOutput
		// RunRaw reports the output in its JSON form; decode it back.
		raw, err := runShell.RunRaw(ctx, in)
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

	<-ctx.Done()
}

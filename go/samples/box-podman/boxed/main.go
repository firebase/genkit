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

// Command boxed is the container side of the box-podman sample: it serves a
// runShell tool, and nothing else. The parent program cross-compiles it for
// the container's Linux VM and runs it there, so it never touches the host.
package main

import (
	"context"
	"os/exec"
	"strings"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	box "github.com/firebase/genkit/go/plugins/box/exp"
)

// ShellInput and ShellOutput match the host's declaration of the tool.
type ShellInput struct {
	Cmd string `json:"cmd" jsonschema_description:"The shell command to run."`
}

type ShellOutput struct {
	Stdout string `json:"stdout,omitempty"`
	Error  string `json:"error,omitempty"`
}

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx)
	genkit.DefineTool(g, "runShell", "Run a shell command and return its stdout.",
		func(tc *ai.ToolContext, in ShellInput) (ShellOutput, error) {
			ctx, cancel := context.WithTimeout(tc, 10*time.Second)
			defer cancel()
			out, err := exec.CommandContext(ctx, "sh", "-c", in.Cmd).CombinedOutput()
			res := ShellOutput{Stdout: strings.TrimSpace(string(out))}
			if err != nil {
				res.Error = err.Error()
			}
			return res, nil
		})
	// Serve until the runner stops the container.
	box.ServeIfRuntime(ctx)
}

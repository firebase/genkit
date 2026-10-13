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

// Command podmanbox is the box entry the podman integration test builds for
// the container: a few actions that report where they run.
package main

import (
	"context"
	"net"
	"os"
	"runtime"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	box "github.com/firebase/genkit/go/plugins/box/exp"
)

type Where struct {
	GOOS    string `json:"goos"`
	Secret  string `json:"secret"`
	Egress  bool   `json:"egress"`
	Passed  string `json:"passed"`
	WorkDir string `json:"workDir"`
}

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx)
	genkit.DefineTool(g, "where", "Reports where the box runs.", func(_ *ai.ToolContext, _ struct{}) (Where, error) {
		wd, _ := os.Getwd()
		conn, err := net.DialTimeout("tcp", "1.1.1.1:53", 2*time.Second)
		if err == nil {
			conn.Close()
		}
		return Where{
			GOOS:    runtime.GOOS,
			Secret:  os.Getenv("HOST_ONLY_SECRET"),
			Egress:  err == nil,
			Passed:  os.Getenv("PASSED"),
			WorkDir: wd,
		}, nil
	})
	box.ServeIfRuntime(ctx)
}

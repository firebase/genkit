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
	"os/exec"
	"testing"
	"time"
)

// TestPodmanEndToEnd cross-compiles testdata/podmanbox, runs it in a real
// container, and checks containment. It needs a running podman; it is
// skipped otherwise, and in -short mode.
func TestPodmanEndToEnd(t *testing.T) {
	if testing.Short() {
		t.Skip("needs a container engine")
	}
	if err := exec.Command("podman", "info").Run(); err != nil {
		t.Skip("podman is not available")
	}
	ctx := context.Background()
	t.Setenv("HOST_ONLY_SECRET", "s3cret")
	wd, _ := os.Getwd()
	b := New(newTestGenkit(), PodmanRunner(PodmanOptions{
		Image:        "docker.io/library/alpine:3",
		Build:        &GoBuild{Package: "./testdata/podmanbox"},
		Env:          map[string]string{"PASSED": "in"},
		ReadyTimeout: 2 * time.Minute,
	}))
	t.Cleanup(func() { _ = b.Close(ctx) })

	type where struct {
		GOOS    string `json:"goos"`
		Secret  string `json:"secret"`
		Egress  bool   `json:"egress"`
		Passed  string `json:"passed"`
		WorkDir string `json:"workDir"`
	}
	var got where
	raw, err := NewTool[struct{}, where](b, "where", "").RunRaw(ctx, map[string]any{})
	if err != nil {
		t.Fatal(err)
	}
	m := raw.(map[string]any)
	got.GOOS, _ = m["goos"].(string)
	got.Secret, _ = m["secret"].(string)
	got.Egress, _ = m["egress"].(bool)
	got.Passed, _ = m["passed"].(string)
	got.WorkDir, _ = m["workDir"].(string)

	if got.GOOS != "linux" {
		t.Errorf("goos = %q, want linux", got.GOOS)
	}
	if got.Secret != "" {
		t.Error("the container inherited a host env var")
	}
	if got.Passed != "in" {
		t.Errorf("PASSED = %q, want the value from Env", got.Passed)
	}
	if got.Egress {
		t.Error("the container reached the internet on the internal network")
	}
	if got.WorkDir != realPath(wd) {
		t.Errorf("workdir = %q, want the project dir %q", got.WorkDir, realPath(wd))
	}
}

// Copyright 2024 Google LLC
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

package main

import (
	"flag"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

var update = flag.Bool("update", false, "update golden")

func Test(t *testing.T) {
	if _, err := exec.LookPath("diff"); err != nil {
		t.Skip("skipping; no diff program")
	}
	const pkgPath = "test"
	outDir := t.TempDir()
	err := run(
		filepath.Join("testdata", "test.json"),
		pkgPath,
		filepath.Join("testdata", "test.config"),
		outDir)
	if err != nil {
		t.Fatal(err)
	}
	outFile := filepath.Join(outDir, pkgPath, "gen.go")
	goldenFile := filepath.Join("testdata", "golden")
	if *update {
		if err := os.Rename(outFile, goldenFile); err != nil {
			t.Fatal(err)
		}
		t.Log("updated golden")
	} else {
		out, err := exec.Command("diff", "-u", goldenFile, outFile).CombinedOutput()
		if err != nil {
			t.Fatalf("%v\n%s", err, out)
		}
		if len(out) > 0 {
			t.Errorf("%s", out)
		}
	}
}

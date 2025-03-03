// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

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

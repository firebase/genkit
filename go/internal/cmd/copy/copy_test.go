// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package main

import (
	"path/filepath"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
	"golang.org/x/tools/txtar"
)

func TestParseCommand(t *testing.T) {
	for _, test := range []struct {
		line    string
		want    *command
		wantErr bool
	}{
		{"", nil, false},
		{"x", nil, false},
		{"//coopy:x", nil, false},
		{"// copy:x", nil, false},
		{"//copy:start", nil, true},
		{"//copy:start file sink", &command{"start", "file", "sink"}, false},
		{"//copy:stop", &command{name: "stop"}, false},
		{"//copy:sink foo", &command{name: "sink", sink: "foo"}, false},
		{"//copy:endsink bar", &command{name: "endsink", sink: "bar"}, false},
	} {
		got, err := parseCommand([]byte(test.line))
		if err != nil {
			if !test.wantErr {
				t.Fatalf("%q: got error %q", test.line, err)
			}
			continue
		}
		if !cmp.Equal(got, test.want, cmp.AllowUnexported(command{})) {
			t.Errorf("%q:\ngot  %+v\nwant %+v", test.line, got, test.want)
		}

	}
}

func TestFull(t *testing.T) {
	files, err := filepath.Glob(filepath.Join("testdata", "*.txt"))
	if err != nil {
		t.Fatal(err)
	}

	doit := func(t *testing.T, dest, src []byte) []byte {
		chunks, err := parseSource(src)
		if err != nil {
			t.Fatal(err)
		}
		if err := setChunkFilenames(chunks, "source", ""); err != nil {
			t.Fatal(err)
		}
		pieces, err := parseDest(dest)
		if err != nil {
			t.Fatal(err)
		}
		if err := insertChunksIntoPieces(pieces, chunks); err != nil {
			t.Fatal(err)
		}
		return concatPieces(pieces)
	}

	for _, file := range files {
		t.Run(strings.TrimPrefix(filepath.Base(file), ".txt"), func(t *testing.T) {
			ar, err := txtar.ParseFile(file)
			if err != nil {
				t.Fatal(err)
			}
			var source, dest, want txtar.File
			for _, f := range ar.Files {
				switch f.Name {
				case "source":
					source = f
				case "dest":
					dest = f
				case "want":
					want = f
				default:
					t.Fatal("unknown txtar filename")
				}
			}
			got := doit(t, dest.Data, source.Data)
			if diff := cmp.Diff(want.Data, got); diff != "" {
				t.Errorf("mismatch (-want, +got)\n%s", diff)
			}

			// Running it on the output should produce the same result.
			got = doit(t, got, source.Data)
			if diff := cmp.Diff(want.Data, got); diff != "" {
				t.Errorf("second time: mismatch (-want, +got)\n%s", diff)
			}
		})
	}
}

func TestUnused(t *testing.T) {
	chunks := []*chunk{{sink: "S"}}
	pieces := []*piece{{sink: "T"}}
	err := insertChunksIntoPieces(pieces, chunks)
	if err == nil {
		t.Fatal("want error")
	}
}

func TestRelativePathTo(t *testing.T) {
	for _, test := range []struct {
		p1, p2 string
		want   string
	}{
		{"a", "b", "a"},
		{"d/a", "d/b", "a"},
		{"d1/a", "b", "d1/a"},
		{"a", "d1/b", "../a"},
		{"d1/a", "d2/b", "../d1/a"},
		{"g.go", "../vertexai/v.go", "../copy/g.go"},
	} {
		got, err := relativePathTo(test.p1, test.p2)
		if err != nil {
			t.Fatal(err)
		}
		if got != test.want {
			t.Errorf("relativePathTo(%q, %q) = %q, want %q", test.p1, test.p2, got, test.want)
		}
	}
}

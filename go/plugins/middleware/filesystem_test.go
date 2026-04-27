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

package middleware

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/registry"
)

// makeFS creates a temp directory populated with a small fixture and returns
// its path. Layout:
//
//	root/
//	  hello.txt         ("hello world")
//	  docs/README.md    ("# Docs")
//	  docs/nested/x.txt ("nested")
func makeFS(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	write := func(relPath, body string) {
		p := filepath.Join(root, filepath.FromSlash(relPath))
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	write("hello.txt", "hello world")
	write("docs/README.md", "# Docs")
	write("docs/nested/x.txt", "nested")
	return root
}

// toolScriptedModel returns a model that walks through the provided script of
// turns. On turn i the model emits script[i], which is either a list of tool
// requests (triggering the tool loop) or a final text response.
//
// This lets tests drive deterministic multi-turn conversations without a real
// LLM while exercising the middleware's full lifecycle.
type modelTurn struct {
	// If Tools is non-empty, the model issues these tool requests.
	Tools []*ai.ToolRequest
	// Otherwise, the model returns this text as the final response.
	Text string
}

func scriptedModel(t *testing.T, r *registry.Registry, name string, script []modelTurn) (ai.Model, *[]*ai.ModelRequest) {
	t.Helper()
	var seen []*ai.ModelRequest
	idx := 0
	m := ai.DefineModel(r, name, &ai.ModelOptions{
		Supports: &ai.ModelSupports{Multiturn: true, SystemRole: true, Tools: true, Media: true},
	}, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		seen = append(seen, req)
		if idx >= len(script) {
			return &ai.ModelResponse{Request: req, Message: ai.NewModelTextMessage("unexpected extra turn")}, nil
		}
		turn := script[idx]
		idx++
		if len(turn.Tools) > 0 {
			content := make([]*ai.Part, 0, len(turn.Tools))
			for _, tr := range turn.Tools {
				content = append(content, ai.NewToolRequestPart(tr))
			}
			return &ai.ModelResponse{Request: req, Message: &ai.Message{Role: ai.RoleModel, Content: content}}, nil
		}
		return &ai.ModelResponse{Request: req, Message: ai.NewModelTextMessage(turn.Text)}, nil
	})
	return m, &seen
}

func TestFilesystemListFilesNonRecursive(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	m, _ := scriptedModel(t, r, "test/fs-list", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name:  "list_files",
			Input: map[string]any{"dirPath": ""},
		}}},
		{Text: "done"},
	})

	fs := &Filesystem{RootDir: root}
	ai.DefineMiddleware(r, "filesystem", fs)

	resp, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs))
	if err != nil {
		t.Fatal(err)
	}
	if resp.Text() != "done" {
		t.Fatalf("final text = %q, want %q", resp.Text(), "done")
	}

	// Find the tool response part and check that top-level entries came back.
	var got []fileEntry
	for _, msg := range resp.History() {
		for _, p := range msg.Content {
			if p.IsToolResponse() && p.ToolResponse.Name == "list_files" {
				// Output comes back as a []any from JSON round-trip.
				if list, ok := p.ToolResponse.Output.([]any); ok {
					for _, e := range list {
						m, _ := e.(map[string]any)
						name, _ := m["path"].(string)
						isDir, _ := m["isDirectory"].(bool)
						got = append(got, fileEntry{Path: name, IsDirectory: isDir})
					}
				}
			}
		}
	}

	sort.Slice(got, func(i, j int) bool { return got[i].Path < got[j].Path })
	want := []fileEntry{
		{Path: "docs", IsDirectory: true},
		{Path: "hello.txt", IsDirectory: false},
	}
	if len(got) != len(want) {
		t.Fatalf("entries = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("entry[%d] = %v, want %v", i, got[i], want[i])
		}
	}
}

func TestFilesystemListFilesRecursive(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	m, _ := scriptedModel(t, r, "test/fs-list-r", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name:  "list_files",
			Input: map[string]any{"dirPath": "docs", "recursive": true},
		}}},
		{Text: "done"},
	})

	fs := &Filesystem{RootDir: root}
	ai.DefineMiddleware(r, "filesystem", fs)

	resp, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs))
	if err != nil {
		t.Fatal(err)
	}

	paths := map[string]bool{}
	for _, msg := range resp.History() {
		for _, p := range msg.Content {
			if p.IsToolResponse() && p.ToolResponse.Name == "list_files" {
				if list, ok := p.ToolResponse.Output.([]any); ok {
					for _, e := range list {
						m, _ := e.(map[string]any)
						name, _ := m["path"].(string)
						paths[name] = true
					}
				}
			}
		}
	}
	for _, want := range []string{"README.md", "nested", filepath.ToSlash(filepath.Join("nested", "x.txt"))} {
		if !paths[want] {
			t.Errorf("recursive list missing %q; got %v", want, paths)
		}
	}
}

func TestFilesystemReadFileInjectsUserMessage(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	m, seen := scriptedModel(t, r, "test/fs-read", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name:  "read_file",
			Input: map[string]any{"filePath": "hello.txt"},
		}}},
		{Text: "done"},
	})

	fs := &Filesystem{RootDir: root}
	ai.DefineMiddleware(r, "filesystem", fs)

	if _, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs)); err != nil {
		t.Fatal(err)
	}

	if len(*seen) < 2 {
		t.Fatalf("expected at least 2 model calls, got %d", len(*seen))
	}
	second := (*seen)[1]

	// The injected user message must carry the file contents.
	var found bool
	for _, msg := range second.Messages {
		if msg.Role != ai.RoleUser {
			continue
		}
		for _, p := range msg.Content {
			if p.IsText() && strings.Contains(p.Text, "hello world") &&
				strings.Contains(p.Text, `path="hello.txt"`) {
				found = true
			}
		}
	}
	if !found {
		t.Errorf("file content not injected as user message on turn 2; got messages=%v", second.Messages)
	}
}

func TestFilesystemReadFileInjectsImageAsMedia(t *testing.T) {
	r := newTestRegistry(t)
	root := t.TempDir()

	// Tiny 1x1 transparent PNG.
	img := []byte{
		0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
		0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x06, 0x00, 0x00, 0x00, 0x1f, 0x15, 0xc4, 0x89, 0x00, 0x00, 0x00,
		0x0a, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9c, 0x63, 0x00, 0x01, 0x00, 0x00,
		0x05, 0x00, 0x01, 0x0d, 0x0a, 0x2d, 0xb4, 0x00, 0x00, 0x00, 0x00, 0x49,
		0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
	}
	if err := os.WriteFile(filepath.Join(root, "pixel.png"), img, 0o644); err != nil {
		t.Fatal(err)
	}

	m, seen := scriptedModel(t, r, "test/fs-img", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name:  "read_file",
			Input: map[string]any{"filePath": "pixel.png"},
		}}},
		{Text: "done"},
	})

	fs := &Filesystem{RootDir: root}
	ai.DefineMiddleware(r, "filesystem", fs)

	if _, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs)); err != nil {
		t.Fatal(err)
	}
	if len(*seen) < 2 {
		t.Fatalf("expected 2 model calls, got %d", len(*seen))
	}

	foundMedia := false
	for _, msg := range (*seen)[1].Messages {
		if msg.Role != ai.RoleUser {
			continue
		}
		for _, p := range msg.Content {
			if p.IsMedia() && strings.HasPrefix(p.ContentType, "image/png") {
				foundMedia = true
			}
		}
	}
	if !foundMedia {
		t.Errorf("expected an image media part in the injected user message")
	}
}

// TestFilesystemStreamsInjectedFileContents verifies that when read_file runs
// and the next turn begins, the injected user message carrying the file contents
// is emitted to the streaming callback with the correct sequential index, so
// consumers of GenerateStream see it alongside the model and tool messages.
func TestFilesystemStreamsInjectedFileContents(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	// Streaming model that emits the same payload it returns, so each turn
	// produces at least one chunk.
	turn := 0
	m := ai.DefineModel(r, "test/fs-stream", &ai.ModelOptions{
		Supports: &ai.ModelSupports{Multiturn: true, SystemRole: true, Tools: true, Media: true},
	}, func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		turn++
		if turn == 1 {
			content := []*ai.Part{ai.NewToolRequestPart(&ai.ToolRequest{
				Name:  "read_file",
				Input: map[string]any{"filePath": "hello.txt"},
			})}
			if cb != nil {
				if err := cb(ctx, &ai.ModelResponseChunk{Content: content}); err != nil {
					return nil, err
				}
			}
			return &ai.ModelResponse{Request: req, Message: &ai.Message{Role: ai.RoleModel, Content: content}}, nil
		}
		content := []*ai.Part{ai.NewTextPart("done")}
		if cb != nil {
			if err := cb(ctx, &ai.ModelResponseChunk{Content: content}); err != nil {
				return nil, err
			}
		}
		return &ai.ModelResponse{Request: req, Message: &ai.Message{Role: ai.RoleModel, Content: content}}, nil
	})

	fs := &Filesystem{RootDir: root}
	ai.DefineMiddleware(r, "filesystem", fs)

	var chunks []*ai.ModelResponseChunk
	if _, err := ai.Generate(ctx, r,
		ai.WithModel(m),
		ai.WithPrompt("go"),
		ai.WithUse(fs),
		ai.WithStreaming(func(_ context.Context, c *ai.ModelResponseChunk) error {
			chunks = append(chunks, c)
			return nil
		}),
	); err != nil {
		t.Fatal(err)
	}

	// Expect four unique indices in order: model (0), tool (1), injected user (2), model (3).
	var indices []int
	seen := map[int]bool{}
	for _, c := range chunks {
		if !seen[c.Index] {
			seen[c.Index] = true
			indices = append(indices, c.Index)
		}
	}
	want := []int{0, 1, 2, 3}
	if len(indices) != len(want) {
		t.Fatalf("distinct indices = %v, want %v", indices, want)
	}
	for i := range want {
		if indices[i] != want[i] {
			t.Fatalf("indices[%d] = %d, want %d (full: %v)", i, indices[i], want[i], indices)
		}
	}

	// The injected file-content chunk must be at index 2 with RoleUser and
	// carry the file body.
	var injected *ai.ModelResponseChunk
	for _, c := range chunks {
		if c.Index == 2 {
			injected = c
			break
		}
	}
	if injected == nil {
		t.Fatal("no chunk at index 2 for injected file content")
	}
	if injected.Role != ai.RoleUser {
		t.Errorf("injected chunk role = %q, want %q", injected.Role, ai.RoleUser)
	}
	var hasFileBody bool
	for _, p := range injected.Content {
		if p.IsText() && strings.Contains(p.Text, "hello world") {
			hasFileBody = true
		}
	}
	if !hasFileBody {
		t.Errorf("injected chunk missing file body; got %+v", injected.Content)
	}
}

func TestFilesystemWriteFileRequiresAllowWriteAccess(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	// Only list_files/read_file should be registered; write_file must not be.
	fs := &Filesystem{RootDir: root}
	ai.DefineMiddleware(r, "filesystem", fs)

	hooks, err := fs.New(ctx)
	if err != nil {
		t.Fatal(err)
	}
	names := map[string]bool{}
	for _, tool := range hooks.Tools {
		names[tool.Name()] = true
	}
	if !names["list_files"] || !names["read_file"] {
		t.Errorf("read-only config missing expected tools; got %v", names)
	}
	if names["write_file"] || names["search_and_replace"] {
		t.Errorf("read-only config exposed write tools; got %v", names)
	}
}

func TestFilesystemWriteFileCreatesAndOverwrites(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	m, _ := scriptedModel(t, r, "test/fs-write", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name: "write_file",
			Input: map[string]any{
				"filePath": "sub/new.txt",
				"content":  "fresh content",
			},
		}}},
		{Text: "done"},
	})

	fs := &Filesystem{RootDir: root, AllowWriteAccess: true}
	ai.DefineMiddleware(r, "filesystem", fs)

	if _, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs)); err != nil {
		t.Fatal(err)
	}

	got, err := os.ReadFile(filepath.Join(root, "sub", "new.txt"))
	if err != nil {
		t.Fatalf("expected file to exist: %v", err)
	}
	if string(got) != "fresh content" {
		t.Errorf("content = %q, want %q", got, "fresh content")
	}
}

func TestFilesystemSearchAndReplace(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	edit := "<<<<<<< SEARCH\nhello world\n=======\nhello there\n>>>>>>> REPLACE"
	m, _ := scriptedModel(t, r, "test/fs-sr", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name: "search_and_replace",
			Input: map[string]any{
				"filePath": "hello.txt",
				"edits":    []any{edit},
			},
		}}},
		{Text: "done"},
	})

	fs := &Filesystem{RootDir: root, AllowWriteAccess: true}
	ai.DefineMiddleware(r, "filesystem", fs)

	if _, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs)); err != nil {
		t.Fatal(err)
	}

	got, err := os.ReadFile(filepath.Join(root, "hello.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "hello there" {
		t.Errorf("content = %q, want %q", got, "hello there")
	}
}

func TestFilesystemSearchAndReplaceNotFound(t *testing.T) {
	// When the search content can't be located, the tool call should fail,
	// and the failure should surface to the model as a placeholder tool
	// response plus a user message, rather than crashing the generation.
	r := newTestRegistry(t)
	root := makeFS(t)

	edit := "<<<<<<< SEARCH\nNOT THERE\n=======\nREPLACED\n>>>>>>> REPLACE"
	m, seen := scriptedModel(t, r, "test/fs-sr-miss", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name: "search_and_replace",
			Input: map[string]any{
				"filePath": "hello.txt",
				"edits":    []any{edit},
			},
		}}},
		{Text: "recovered"},
	})

	fs := &Filesystem{RootDir: root, AllowWriteAccess: true}
	ai.DefineMiddleware(r, "filesystem", fs)

	resp, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs))
	if err != nil {
		t.Fatal(err)
	}
	if resp.Text() != "recovered" {
		t.Errorf("final text = %q, want %q", resp.Text(), "recovered")
	}

	// File must be untouched.
	got, err := os.ReadFile(filepath.Join(root, "hello.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "hello world" {
		t.Errorf("file modified despite failed edit: %q", got)
	}

	// The second turn should have received an injected user message carrying
	// the tool failure.
	if len(*seen) < 2 {
		t.Fatalf("expected 2 model calls, got %d", len(*seen))
	}
	found := false
	for _, msg := range (*seen)[1].Messages {
		if msg.Role != ai.RoleUser {
			continue
		}
		for _, p := range msg.Content {
			if p.IsText() && strings.Contains(p.Text, `Tool "search_and_replace" failed`) {
				found = true
			}
		}
	}
	if !found {
		t.Errorf("expected a user message describing the tool failure")
	}
}

func TestFilesystemRejectsTraversal(t *testing.T) {
	r := newTestRegistry(t)
	root := makeFS(t)

	// Create a sibling directory that the model should not be able to reach
	// via traversal.
	sibling := filepath.Join(filepath.Dir(root), "sibling-secret")
	if err := os.MkdirAll(sibling, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(sibling, "secret.txt"), []byte("nope"), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.RemoveAll(sibling) })

	m, seen := scriptedModel(t, r, "test/fs-trav", []modelTurn{
		{Tools: []*ai.ToolRequest{{
			Name:  "read_file",
			Input: map[string]any{"filePath": "../sibling-secret/secret.txt"},
		}}},
		{Text: "ok"},
	})

	fs := &Filesystem{RootDir: root}
	ai.DefineMiddleware(r, "filesystem", fs)

	if _, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs)); err != nil {
		t.Fatal(err)
	}

	// The read must not have leaked the sibling file. Instead, the generation
	// should see a failure message.
	if len(*seen) < 2 {
		t.Fatalf("expected 2 model calls, got %d", len(*seen))
	}
	found := false
	for _, msg := range (*seen)[1].Messages {
		if msg.Role != ai.RoleUser {
			continue
		}
		for _, p := range msg.Content {
			if p.IsText() && strings.Contains(p.Text, `"read_file" failed`) {
				found = true
			}
			if p.IsText() && strings.Contains(p.Text, "nope") {
				t.Errorf("sibling file contents leaked to the model")
			}
		}
	}
	if !found {
		t.Errorf("expected traversal attempt to surface as a failure message")
	}
}

func TestFilesystemToolNamePrefix(t *testing.T) {
	root := makeFS(t)

	fs := &Filesystem{RootDir: root, AllowWriteAccess: true, ToolNamePrefix: "fs_"}
	hooks, err := fs.New(ctx)
	if err != nil {
		t.Fatal(err)
	}
	names := map[string]bool{}
	for _, tool := range hooks.Tools {
		names[tool.Name()] = true
	}
	for _, want := range []string{"fs_list_files", "fs_read_file", "fs_write_file", "fs_search_and_replace"} {
		if !names[want] {
			t.Errorf("expected prefixed tool %q; got %v", want, names)
		}
	}
}

// TestFilesystemRespectsConfigOverride verifies that when the middleware is
// invoked via GenerateWithRequest (the path the Dev UI uses) with a config
// that differs from the prototype originally registered, the tools operate
// against the override config — not the prototype's.
func TestFilesystemRespectsConfigOverride(t *testing.T) {
	r := newTestRegistry(t)

	protoRoot := t.TempDir()
	if err := os.WriteFile(filepath.Join(protoRoot, "marker.txt"), []byte("from-proto"), 0o644); err != nil {
		t.Fatal(err)
	}
	overrideRoot := t.TempDir()
	if err := os.WriteFile(filepath.Join(overrideRoot, "marker.txt"), []byte("from-override"), 0o644); err != nil {
		t.Fatal(err)
	}

	// Register the middleware with the proto root.
	ai.DefineMiddleware(r, "filesystem", &Filesystem{RootDir: protoRoot})

	m, seen := scriptedModel(t, r, "test/fs-devui", []modelTurn{
		{Tools: []*ai.ToolRequest{{Name: "read_file", Input: map[string]any{"filePath": "marker.txt"}}}},
		{Text: "done"},
	})

	// Invoke GenerateWithRequest with a config override — simulating the Dev
	// UI sending different config JSON.
	actionOpts := &ai.GenerateActionOptions{
		Model:    m.Name(),
		Messages: []*ai.Message{ai.NewUserTextMessage("go")},
		Use: []*ai.MiddlewareRef{{
			Name:   (&Filesystem{}).Name(),
			Config: map[string]any{"rootDirectory": overrideRoot},
		}},
	}

	if _, err := ai.GenerateWithRequest(ctx, r, actionOpts, nil, nil); err != nil {
		t.Fatal(err)
	}
	if len(*seen) < 2 {
		t.Fatalf("expected 2 model calls, got %d", len(*seen))
	}

	var found bool
	for _, msg := range (*seen)[1].Messages {
		for _, p := range msg.Content {
			if p.IsText() && strings.Contains(p.Text, "from-override") {
				found = true
			}
			if p.IsText() && strings.Contains(p.Text, "from-proto") {
				t.Errorf("tool read from prototype root instead of override config")
			}
		}
	}
	if !found {
		t.Errorf("expected override-root content in injected user message")
	}
}

func TestFilesystemMissingRootDirIsAnError(t *testing.T) {
	r := newTestRegistry(t)

	m, _ := scriptedModel(t, r, "test/fs-nomissing", []modelTurn{
		{Text: "unreachable"},
	})

	fs := &Filesystem{}
	ai.DefineMiddleware(r, "filesystem", fs)

	_, err := ai.Generate(ctx, r, ai.WithModel(m), ai.WithPrompt("go"), ai.WithUse(fs))
	if err == nil {
		t.Fatal("expected an error when RootDir is unset")
	}
	if !strings.Contains(err.Error(), "RootDir is required") {
		t.Errorf("error = %q; want to mention RootDir", err.Error())
	}
}

func TestApplySearchReplaceAmbiguousSeparators(t *testing.T) {
	// When the same "=======" string appears in the SEARCH half (e.g. because
	// the file contains it), both split positions parse as valid blocks. The
	// longer matching search must win.
	content := "line1\n=======\nline2"

	block := "<<<<<<< SEARCH\nline1\n=======\nline2\n=======\nREPLACED\n>>>>>>> REPLACE"

	got, err := applySearchReplace(content, block, "x.txt")
	if err != nil {
		t.Fatal(err)
	}
	if got != "REPLACED" {
		t.Errorf("got %q, want %q", got, "REPLACED")
	}
}

func TestApplySearchReplaceInvalidBlock(t *testing.T) {
	cases := []string{
		"no markers at all",
		"<<<<<<< SEARCH\nonly search\n>>>>>>> REPLACE",
		"<<<<<<< SEARCH\na\n=======\n",   // missing end
		"a\n=======\nb\n>>>>>>> REPLACE", // missing start
	}
	for _, b := range cases {
		if _, err := applySearchReplace("anything", b, "x"); err == nil {
			t.Errorf("expected error for block %q", b)
		}
	}
}

func TestNormalizeRel(t *testing.T) {
	// Normalisation is platform-sensitive only for leading-slash stripping,
	// so keep the table in slash form and verify via path.Clean semantics.
	cases := []struct {
		in, want string
	}{
		{"", "."},
		{"   ", "."},
		{"foo/bar", "foo/bar"},
		{"/foo/bar", "foo/bar"},
		{"//foo//bar", "foo/bar"},
		{"./foo", "foo"},
		// We don't try to sanitise ".." here; os.Root enforces the final rule.
	}
	if runtime.GOOS == "windows" {
		cases = append(cases, struct{ in, want string }{`foo\bar`, "foo/bar"})
	}
	for _, c := range cases {
		if got := normalizeRel(c.in); got != c.want {
			t.Errorf("normalizeRel(%q) = %q; want %q", c.in, got, c.want)
		}
	}
}

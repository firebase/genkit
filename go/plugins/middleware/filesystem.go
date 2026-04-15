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
	"encoding/base64"
	"errors"
	"fmt"
	"io/fs"
	"mime"
	"os"
	"path"
	"path/filepath"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
)

// SEARCH/REPLACE block markers used by the search_and_replace tool.
const (
	searchReplaceStart     = "<<<<<<< SEARCH\n"
	searchReplaceEnd       = "\n>>>>>>> REPLACE"
	searchReplaceSeparator = "\n=======\n"
)

// Filesystem is a middleware that grants the LLM scoped file access under a
// single root directory. It registers list_files and read_file, plus
// write_file and search_and_replace when AllowWriteAccess is true.
//
// Path safety is enforced by [os.Root] (Go 1.24+), which rejects any path
// that resolves outside the root, including via "..", absolute paths, or
// symbolic links.
//
// Usage:
//
//	resp, err := genkit.Generate(ctx, g,
//	    ai.WithModel(m),
//	    ai.WithPrompt("summarise docs/ and save the summary to out.md"),
//	    ai.WithUse(&middleware.Filesystem{
//	        RootDir:          "./workspace",
//	        AllowWriteAccess: true,
//	    }),
//	)
type Filesystem struct {
	ai.BaseMiddleware

	// RootDir is the directory that all operations are confined to.
	RootDir string `json:"rootDirectory,omitempty"`
	// AllowWriteAccess adds write_file and search_and_replace.
	AllowWriteAccess bool `json:"allowWriteAccess,omitempty"`
	// ToolNamePrefix is prepended to each tool name. Use distinct prefixes
	// when attaching multiple Filesystem middlewares to one call so their
	// tool names don't collide.
	ToolNamePrefix string `json:"toolNamePrefix,omitempty"`

	initOnce sync.Once
	root     *os.Root
	tools    []ai.Tool
	toolSet  map[string]struct{}
	initErr  error

	mu    sync.Mutex
	queue []*ai.Message
}

func (f *Filesystem) Name() string { return provider + "/filesystem" }

func (f *Filesystem) New() ai.Middleware {
	return &Filesystem{
		RootDir:          f.RootDir,
		AllowWriteAccess: f.AllowWriteAccess,
		ToolNamePrefix:   f.ToolNamePrefix,
	}
}

func (f *Filesystem) init() error {
	f.initOnce.Do(func() {
		if strings.TrimSpace(f.RootDir) == "" {
			f.initErr = core.NewError(core.INVALID_ARGUMENT, "filesystem middleware: RootDir is required")
			return
		}
		abs, err := filepath.Abs(f.RootDir)
		if err != nil {
			f.initErr = core.NewError(core.INTERNAL, "filesystem middleware: resolve %q: %v", f.RootDir, err)
			return
		}
		root, err := os.OpenRoot(abs)
		if err != nil {
			f.initErr = core.NewError(core.FAILED_PRECONDITION, "filesystem middleware: open root %q: %v", abs, err)
			return
		}
		f.root = root
		f.tools = f.buildTools()
		f.toolSet = make(map[string]struct{}, len(f.tools))
		for _, t := range f.tools {
			f.toolSet[t.Name()] = struct{}{}
		}
	})
	return f.initErr
}

// toolName returns suffix prefixed with f.ToolNamePrefix.
func (f *Filesystem) toolName(suffix string) string { return f.ToolNamePrefix + suffix }

// Tools returns nil on a configuration error; WrapGenerate surfaces the error
// through the first model call so the user sees it instead of "tool not found".
func (f *Filesystem) Tools() []ai.Tool {
	if err := f.init(); err != nil {
		return nil
	}
	return f.tools
}

func (f *Filesystem) WrapGenerate(ctx context.Context, params *ai.GenerateParams, next ai.GenerateNext) (*ai.ModelResponse, error) {
	if err := f.init(); err != nil {
		return nil, err
	}

	f.mu.Lock()
	queued := f.queue
	f.queue = nil
	f.mu.Unlock()

	if len(queued) > 0 {
		if params.Callback != nil {
			for _, msg := range queued {
				if err := params.Callback(ctx, &ai.ModelResponseChunk{
					Role:    msg.Role,
					Index:   params.MessageIndex,
					Content: msg.Content,
				}); err != nil {
					return nil, err
				}
				params.MessageIndex++
			}
		}
		params.Request.Messages = append(params.Request.Messages, queued...)
	}

	return next(ctx, params)
}

// WrapTool converts failures from this middleware's tools into a placeholder
// tool response plus an appended user message so the model can retry. Other
// tools pass through. Interrupts always propagate.
func (f *Filesystem) WrapTool(ctx context.Context, params *ai.ToolParams, next ai.ToolNext) (*ai.ToolResponse, error) {
	if _, ours := f.toolSet[params.Tool.Name()]; !ours {
		return next(ctx, params)
	}

	resp, err := next(ctx, params)
	if err == nil {
		return resp, nil
	}
	if isInterrupt, _ := ai.IsToolInterruptError(err); isInterrupt {
		return nil, err
	}

	f.enqueueParts(ai.NewTextPart(fmt.Sprintf("Tool %q failed: %v", params.Tool.Name(), err)))
	return &ai.ToolResponse{
		Name:   params.Request.Name,
		Ref:    params.Request.Ref,
		Output: "Tool call failed; see user message below for details.",
	}, nil
}

// enqueueParts appends parts to the last user message in the queue or starts
// a new one. Safe for concurrent tool calls within a single Generate.
func (f *Filesystem) enqueueParts(parts ...*ai.Part) {
	f.mu.Lock()
	defer f.mu.Unlock()
	if n := len(f.queue); n > 0 && f.queue[n-1].Role == ai.RoleUser {
		f.queue[n-1].Content = append(f.queue[n-1].Content, parts...)
		return
	}
	f.queue = append(f.queue, ai.NewUserMessage(parts...))
}

func (f *Filesystem) buildTools() []ai.Tool {
	tools := []ai.Tool{f.newListFilesTool(), f.newReadFileTool()}
	if f.AllowWriteAccess {
		tools = append(tools, f.newWriteFileTool(), f.newSearchReplaceTool())
	}
	return tools
}

// normalizeRel canonicalises an LLM-supplied path into a slash-separated
// relative path. Leading separators are stripped so "/foo" is treated as
// relative to the root; os.Root enforces the final escape check.
func normalizeRel(p string) string {
	p = strings.TrimSpace(p)
	p = filepath.ToSlash(p)
	p = strings.TrimLeft(p, "/")
	if p == "" {
		return "."
	}
	return path.Clean(p)
}

// requireFilePath validates the shared filePath argument used by read_file,
// write_file, and search_and_replace.
func requireFilePath(s string) error {
	if strings.TrimSpace(s) == "" {
		return errors.New("filePath is required")
	}
	return nil
}

type listFilesInput struct {
	DirPath   string `json:"dirPath,omitempty" jsonschema:"description=Directory path relative to root. Defaults to the root directory."`
	Recursive bool   `json:"recursive,omitempty" jsonschema:"description=If true, descend into subdirectories."`
}

type fileEntry struct {
	Path        string `json:"path"`
	IsDirectory bool   `json:"isDirectory"`
}

func (f *Filesystem) newListFilesTool() ai.Tool {
	return ai.NewTool(
		f.toolName("list_files"),
		"Lists files and directories in a given path. Returns a list of entries with path and type.",
		func(_ *ai.ToolContext, in listFilesInput) ([]fileEntry, error) {
			dir := normalizeRel(in.DirPath)
			fsys := f.root.FS()

			if !in.Recursive {
				entries, err := fs.ReadDir(fsys, dir)
				if err != nil {
					return nil, err
				}
				out := make([]fileEntry, 0, len(entries))
				for _, e := range entries {
					out = append(out, fileEntry{Path: e.Name(), IsDirectory: e.IsDir()})
				}
				return out, nil
			}

			var out []fileEntry
			err := fs.WalkDir(fsys, dir, func(p string, d fs.DirEntry, err error) error {
				if err != nil {
					return err
				}
				if p == dir {
					return nil
				}
				rel, relErr := filepath.Rel(dir, p)
				if relErr != nil {
					rel = p
				}
				out = append(out, fileEntry{
					Path:        filepath.ToSlash(rel),
					IsDirectory: d.IsDir(),
				})
				return nil
			})
			if err != nil {
				return nil, err
			}
			return out, nil
		},
	)
}

type readFileInput struct {
	FilePath string `json:"filePath" jsonschema:"description=File path relative to root."`
}

func (f *Filesystem) newReadFileTool() ai.Tool {
	return ai.NewTool(
		f.toolName("read_file"),
		"Reads the contents of a file. The actual contents are delivered as a user message on the next turn.",
		func(_ *ai.ToolContext, in readFileInput) (string, error) {
			if err := requireFilePath(in.FilePath); err != nil {
				return "", err
			}
			rel := normalizeRel(in.FilePath)
			mimeType := mime.TypeByExtension(strings.ToLower(path.Ext(rel)))
			data, err := f.root.ReadFile(filepath.FromSlash(rel))
			if err != nil {
				return "", err
			}

			if strings.HasPrefix(mimeType, "image/") {
				encoded := "data:" + mimeType + ";base64," + base64.StdEncoding.EncodeToString(data)
				f.enqueueParts(
					ai.NewTextPart(fmt.Sprintf("\n\nread_file result %s %s", mimeType, in.FilePath)),
					ai.NewMediaPart(mimeType, encoded),
				)
			} else {
				f.enqueueParts(ai.NewTextPart(fmt.Sprintf(
					"<read_file path=%q>\n%s\n</read_file>", in.FilePath, string(data))))
			}
			return fmt.Sprintf("File %s read successfully, see contents below.", in.FilePath), nil
		},
	)
}

type writeFileInput struct {
	FilePath string `json:"filePath" jsonschema:"description=File path relative to root."`
	Content  string `json:"content" jsonschema:"description=Content to write to the file."`
}

func (f *Filesystem) newWriteFileTool() ai.Tool {
	return ai.NewTool(
		f.toolName("write_file"),
		"Writes content to a file, creating it (and any missing parent directories) or overwriting it if it exists.",
		func(_ *ai.ToolContext, in writeFileInput) (string, error) {
			if err := requireFilePath(in.FilePath); err != nil {
				return "", err
			}
			osPath := filepath.FromSlash(normalizeRel(in.FilePath))
			if parent := filepath.Dir(osPath); parent != "." {
				if err := f.root.MkdirAll(parent, 0o755); err != nil {
					return "", fmt.Errorf("create parent dirs: %w", err)
				}
			}
			if err := f.root.WriteFile(osPath, []byte(in.Content), 0o644); err != nil {
				return "", err
			}
			return fmt.Sprintf("File %s written successfully.", in.FilePath), nil
		},
	)
}

type searchReplaceInput struct {
	FilePath string   `json:"filePath" jsonschema:"description=File path relative to root."`
	Edits    []string `json:"edits" jsonschema:"description=SEARCH/REPLACE blocks in the format '<<<<<<< SEARCH\\n[search]\\n=======\\n[replace]\\n>>>>>>> REPLACE'."`
}

func (f *Filesystem) newSearchReplaceTool() ai.Tool {
	return ai.NewTool(
		f.toolName("search_and_replace"),
		"Replaces text in a file using one or more SEARCH/REPLACE blocks. Use this to edit existing files.",
		func(_ *ai.ToolContext, in searchReplaceInput) (string, error) {
			if err := requireFilePath(in.FilePath); err != nil {
				return "", err
			}
			osPath := filepath.FromSlash(normalizeRel(in.FilePath))

			data, err := f.root.ReadFile(osPath)
			if err != nil {
				return "", err
			}
			content := string(data)

			for i, block := range in.Edits {
				next, err := applySearchReplace(content, block, in.FilePath)
				if err != nil {
					return "", fmt.Errorf("edit %d: %w", i, err)
				}
				content = next
			}

			if err := f.root.WriteFile(osPath, []byte(content), 0o644); err != nil {
				return "", err
			}
			return fmt.Sprintf("Successfully applied %d edit(s) to %s.", len(in.Edits), in.FilePath), nil
		},
	)
}

// applySearchReplace applies one SEARCH/REPLACE block to content. The separator
// may legitimately appear in either half of the block, so every candidate
// split is tried and the longest (most specific) matching search wins.
func applySearchReplace(content, block, filePath string) (string, error) {
	if !strings.HasPrefix(block, searchReplaceStart) || !strings.HasSuffix(block, searchReplaceEnd) {
		return "", errors.New(`invalid edit block: must start with "<<<<<<< SEARCH\n" and end with "\n>>>>>>> REPLACE"`)
	}
	inner := block[len(searchReplaceStart) : len(block)-len(searchReplaceEnd)]

	var splits []int
	for i := 0; i < len(inner); {
		off := strings.Index(inner[i:], searchReplaceSeparator)
		if off < 0 {
			break
		}
		splits = append(splits, i+off)
		i = i + off + 1 // +1 so the same match isn't re-found next iteration
	}
	if len(splits) == 0 {
		return "", errors.New(`invalid edit block: missing separator "\n=======\n"`)
	}

	var bestSearch, bestReplace string
	matched := false
	for _, idx := range splits {
		search := inner[:idx]
		replace := inner[idx+len(searchReplaceSeparator):]
		if strings.Contains(content, search) {
			if !matched || len(search) > len(bestSearch) {
				bestSearch, bestReplace = search, replace
			}
			matched = true
		}
	}

	if !matched {
		return "", fmt.Errorf("search content not found in file %s; the search block must match byte-for-byte, including whitespace and indentation", filePath)
	}
	return strings.Replace(content, bestSearch, bestReplace, 1), nil
}

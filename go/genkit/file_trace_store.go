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

package genkit

import (
	"context"
	"encoding/json"
	"errors"
	"io/fs"
	"net/url"
	"os"
	"path/filepath"
)

// A FileTraceStore is a TraceStore that writes traces to files.
type FileTraceStore struct {
	dir string
}

// NewFileTraceStore creates a FileTraceStore that writes traces to the given
// directory. The directory is created if it does not exist.
func NewFileTraceStore(dir string) (*FileTraceStore, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	return &FileTraceStore{dir: dir}, nil
}

// Save implements [TraceStore.Save].
// It is not safe to call Save concurrently with the same ID.
func (s *FileTraceStore) Save(ctx context.Context, id string, td *TraceData) error {
	existing, err := s.Load(ctx, id)
	if err == nil {
		// Merge the existing spans with the incoming ones.
		// Mutate existing because we know it has no other references.
		for k, v := range td.Spans {
			existing.Spans[k] = v
		}
		existing.DisplayName = td.DisplayName
		existing.StartTime = td.StartTime
		existing.EndTime = td.EndTime
		td = existing
	} else if !errors.Is(err, fs.ErrNotExist) {
		return err
	}
	f, err := os.Create(filepath.Join(s.dir, clean(id)))
	if err != nil {
		return err
	}
	defer func() {
		err = errors.Join(err, f.Close())
	}()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "    ") // make the trace easy to read for debugging
	return enc.Encode(td)
}

// Load implements [TraceStore.Load].
func (s *FileTraceStore) Load(ctx context.Context, id string) (*TraceData, error) {
	return readJSONFile[*TraceData](filepath.Join(s.dir, clean(id)))
}

// List implements [TraceStore.List].
// The result is sorted in an implementation-dependent way that is fixed
// for a given version of this package.
func (s *FileTraceStore) List(ctx context.Context, q *TraceQuery) ([]*TraceData, error) {
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		return nil, err
	}
	var ts []*TraceData
	for _, e := range entries {
		t, err := readJSONFile[*TraceData](filepath.Join(s.dir, e.Name()))
		if err != nil {
			return nil, err
		}
		ts = append(ts, t)
	}
	if q != nil && q.Limit > 0 && len(ts) > q.Limit {
		ts = ts[:q.Limit]
	}
	return ts, nil
}

// readJSONFile reads the contents of filename and JSON-decodes it
// into a value of type T.
func readJSONFile[T any](filename string) (T, error) {
	f, err := os.Open(filename)
	if err != nil {
		return zero[T](), err
	}
	defer f.Close()
	var t T
	if err := json.NewDecoder(f).Decode(&t); err != nil {
		return zero[T](), err
	}
	return t, nil
}

// clean returns a valid filename for id.
func clean(id string) string {
	return url.PathEscape(id)
}

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

package core

import (
	"context"
	"os"
	"path/filepath"

	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/common"
)

// A FileFlowStateStore is a FlowStateStore that writes flowStates to files.
type FileFlowStateStore struct {
	dir string
}

// NewFileFlowStateStore creates a FileFlowStateStore that writes traces to the given
// directory. The directory is created if it does not exist.
func NewFileFlowStateStore(dir string) (*FileFlowStateStore, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return nil, err
	}
	return &FileFlowStateStore{dir: dir}, nil
}

func (s *FileFlowStateStore) Save(ctx context.Context, id string, fs common.FlowStater) error {
	data, err := fs.ToJSON()
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(s.dir, base.Clean(id)), data, 0666)
}

func (s *FileFlowStateStore) Load(ctx context.Context, id string, pfs any) error {
	return base.ReadJSONFile(filepath.Join(s.dir, base.Clean(id)), pfs)
}

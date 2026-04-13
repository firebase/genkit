// Copyright 2025 Google LLC
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

package genkit

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestLocalFileDatasetStoreLifecycle(t *testing.T) {
	root := t.TempDir()
	store, err := NewLocalFileDatasetStore(root)
	if err != nil {
		t.Fatalf("NewLocalFileDatasetStore() error = %v", err)
	}

	now := time.Date(2026, time.April, 13, 10, 30, 0, 0, time.UTC)
	store.now = func() time.Time { return now }

	metadata, err := store.CreateDataset(CreateDatasetRequest{
		DatasetID:    "dataset-1-123456",
		DatasetType:  DatasetTypeFlow,
		TargetAction: "/flow/my-flow",
		Schema: &DatasetSchema{
			InputSchema: map[string]any{"type": "string"},
		},
		Data: []InferenceSample{
			{Input: "hello", Reference: "world"},
			{TestCaseID: "sample-2", Input: map[string]any{"foo": "bar"}},
		},
	})
	if err != nil {
		t.Fatalf("CreateDataset() error = %v", err)
	}

	if metadata.Size != 2 || metadata.Version != 1 {
		t.Fatalf("CreateDataset() metadata = %+v", metadata)
	}
	if metadata.DatasetType != DatasetTypeFlow {
		t.Fatalf("CreateDataset() datasetType = %q", metadata.DatasetType)
	}

	datasetPath := filepath.Join(root, "dataset-1-123456.json")
	rawDataset, err := os.ReadFile(datasetPath)
	if err != nil {
		t.Fatalf("ReadFile(%q) error = %v", datasetPath, err)
	}
	var persisted []DatasetSample
	if err := json.Unmarshal(rawDataset, &persisted); err != nil {
		t.Fatalf("Unmarshal(dataset) error = %v", err)
	}
	if len(persisted) != 2 || persisted[0].TestCaseID == "" || persisted[1].TestCaseID != "sample-2" {
		t.Fatalf("persisted dataset = %+v", persisted)
	}

	listed, err := store.ListDatasets()
	if err != nil {
		t.Fatalf("ListDatasets() error = %v", err)
	}
	if len(listed) != 1 || listed[0].DatasetID != "dataset-1-123456" {
		t.Fatalf("ListDatasets() = %+v", listed)
	}

	fetched, err := store.GetDataset("dataset-1-123456")
	if err != nil {
		t.Fatalf("GetDataset() error = %v", err)
	}
	if len(fetched) != 2 {
		t.Fatalf("GetDataset() len = %d, want 2", len(fetched))
	}

	now = now.Add(time.Minute)
	updated, err := store.UpdateDataset(UpdateDatasetRequest{
		DatasetID:    "dataset-1-123456",
		TargetAction: "/flow/other-flow",
		MetricRefs:   []string{"/evaluator/faithfulness"},
		Data: []InferenceSample{
			{TestCaseID: persisted[0].TestCaseID, Input: "updated", Reference: "world"},
			{Input: "new sample"},
		},
	})
	if err != nil {
		t.Fatalf("UpdateDataset() error = %v", err)
	}

	if updated.Version != 2 || updated.Size != 3 {
		t.Fatalf("UpdateDataset() metadata = %+v", updated)
	}
	if updated.TargetAction != "/flow/other-flow" {
		t.Fatalf("UpdateDataset() targetAction = %q", updated.TargetAction)
	}
	if len(updated.MetricRefs) != 1 || updated.MetricRefs[0] != "/evaluator/faithfulness" {
		t.Fatalf("UpdateDataset() metricRefs = %+v", updated.MetricRefs)
	}

	afterUpdate, err := store.GetDataset("dataset-1-123456")
	if err != nil {
		t.Fatalf("GetDataset(after update) error = %v", err)
	}
	if len(afterUpdate) != 3 || afterUpdate[0].Input != "updated" {
		t.Fatalf("GetDataset(after update) = %+v", afterUpdate)
	}

	if err := store.DeleteDataset("dataset-1-123456"); err != nil {
		t.Fatalf("DeleteDataset() error = %v", err)
	}
	if _, err := os.Stat(datasetPath); !os.IsNotExist(err) {
		t.Fatalf("dataset file still exists, err = %v", err)
	}
	listed, err = store.ListDatasets()
	if err != nil {
		t.Fatalf("ListDatasets(after delete) error = %v", err)
	}
	if len(listed) != 0 {
		t.Fatalf("ListDatasets(after delete) = %+v", listed)
	}
}

func TestDefaultDatasetStoreUsesProjectRoot(t *testing.T) {
	projectRoot := t.TempDir()
	if err := os.WriteFile(filepath.Join(projectRoot, "go.mod"), []byte("module example.com/test\n"), 0644); err != nil {
		t.Fatalf("WriteFile(go.mod) error = %v", err)
	}

	child := filepath.Join(projectRoot, "nested")
	if err := os.MkdirAll(child, 0755); err != nil {
		t.Fatalf("MkdirAll() error = %v", err)
	}

	wd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Getwd() error = %v", err)
	}
	t.Cleanup(func() {
		_ = os.Chdir(wd)
	})
	if err := os.Chdir(child); err != nil {
		t.Fatalf("Chdir() error = %v", err)
	}

	store, err := DefaultDatasetStore()
	if err != nil {
		t.Fatalf("DefaultDatasetStore() error = %v", err)
	}

	want, err := filepath.EvalSymlinks(filepath.Join(projectRoot, ".genkit", "datasets"))
	if err != nil {
		want = filepath.Join(projectRoot, ".genkit", "datasets")
	}
	if store.storeRoot != want {
		t.Fatalf("DefaultDatasetStore() root = %q, want %q", store.storeRoot, want)
	}
}

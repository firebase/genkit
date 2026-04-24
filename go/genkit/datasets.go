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
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"time"

	"github.com/google/uuid"
)

var datasetIDPattern = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9_.-]{4,34}[A-Za-z0-9]$`)

// DatasetType identifies the target surface the dataset is intended for.
type DatasetType string

const (
	DatasetTypeUnknown          DatasetType = "UNKNOWN"
	DatasetTypeFlow             DatasetType = "FLOW"
	DatasetTypeModel            DatasetType = "MODEL"
	DatasetTypeExecutablePrompt DatasetType = "EXECUTABLE_PROMPT"
)

// DatasetSchema describes the shape of the dataset's input and reference values.
type DatasetSchema struct {
	InputSchema     map[string]any `json:"inputSchema,omitempty"`
	ReferenceSchema map[string]any `json:"referenceSchema,omitempty"`
}

// InferenceSample is the user-facing dataset item shape.
type InferenceSample struct {
	TestCaseID string `json:"testCaseId,omitempty"`
	Input      any    `json:"input"`
	Reference  any    `json:"reference,omitempty"`
}

// DatasetSample is the persisted dataset item shape used by the developer UI.
type DatasetSample struct {
	TestCaseID string `json:"testCaseId"`
	Input      any    `json:"input"`
	Reference  any    `json:"reference,omitempty"`
}

// CreateDatasetRequest defines the payload for creating a dataset.
type CreateDatasetRequest struct {
	Data         []InferenceSample `json:"data"`
	DatasetID    string            `json:"datasetId,omitempty"`
	DatasetType  DatasetType       `json:"datasetType"`
	Schema       *DatasetSchema    `json:"schema,omitempty"`
	MetricRefs   []string          `json:"metricRefs,omitempty"`
	TargetAction string            `json:"targetAction,omitempty"`
}

// UpdateDatasetRequest defines the payload for updating a dataset.
type UpdateDatasetRequest struct {
	DatasetID    string            `json:"datasetId"`
	Data         []InferenceSample `json:"data,omitempty"`
	Schema       *DatasetSchema    `json:"schema,omitempty"`
	MetricRefs   []string          `json:"metricRefs,omitempty"`
	TargetAction string            `json:"targetAction,omitempty"`
}

// DatasetMetadata contains the dataset metadata shown in the developer UI.
type DatasetMetadata struct {
	DatasetID    string         `json:"datasetId"`
	Size         int            `json:"size"`
	Schema       *DatasetSchema `json:"schema,omitempty"`
	DatasetType  DatasetType    `json:"datasetType"`
	TargetAction string         `json:"targetAction,omitempty"`
	MetricRefs   []string       `json:"metricRefs"`
	Version      int            `json:"version"`
	CreateTime   string         `json:"createTime"`
	UpdateTime   string         `json:"updateTime"`
}

// LocalFileDatasetStore is the default DatasetStore implementation used by the
// current developer UI. It persists datasets as index.json plus one
// <datasetId>.json file under .genkit/datasets.
type LocalFileDatasetStore struct {
	storeRoot string
	indexFile string
	now       func() time.Time
}

// NewLocalFileDatasetStore creates a dataset store rooted at the provided path.
func NewLocalFileDatasetStore(storeRoot string) (*LocalFileDatasetStore, error) {
	if storeRoot == "" {
		return nil, errors.New("store root is required")
	}
	if err := os.MkdirAll(storeRoot, 0755); err != nil {
		return nil, fmt.Errorf("create dataset store root: %w", err)
	}

	store := &LocalFileDatasetStore{
		storeRoot: storeRoot,
		indexFile: filepath.Join(storeRoot, "index.json"),
		now:       time.Now,
	}

	if _, err := os.Stat(store.indexFile); errors.Is(err, os.ErrNotExist) {
		if err := store.writeMetadataMap(map[string]DatasetMetadata{}); err != nil {
			return nil, err
		}
	} else if err != nil {
		return nil, fmt.Errorf("stat dataset index: %w", err)
	}

	return store, nil
}

// DefaultDatasetStore creates the default dataset store for this project.
//
// Today this is a LocalFileDatasetStore so datasets render in the current
// developer UI. If Genkit adds remote dataset persistence later, introduce that
// abstraction at the consumer boundary rather than coupling callers to the
// current file layout.
func DefaultDatasetStore() (*LocalFileDatasetStore, error) {
	projectRoot, err := findProjectRoot()
	if err != nil {
		return nil, err
	}
	return NewLocalFileDatasetStore(filepath.Join(projectRoot, ".genkit", "datasets"))
}

// CreateDataset writes a new dataset and its metadata using the developer UI's
// current on-disk format.
func (s *LocalFileDatasetStore) CreateDataset(req CreateDatasetRequest) (*DatasetMetadata, error) {
	metadataMap, err := s.readMetadataMap()
	if err != nil {
		return nil, err
	}

	datasetID, err := s.generateDatasetID(req.DatasetID, metadataMap)
	if err != nil {
		return nil, err
	}

	dataset := normalizeInferenceDataset(req.Data)
	if err := writeJSONFile(s.datasetFilePath(datasetID), dataset); err != nil {
		return nil, fmt.Errorf("write dataset: %w", err)
	}

	now := s.now().String()
	metricRefs := cloneStrings(req.MetricRefs)
	metadata := DatasetMetadata{
		DatasetID:    datasetID,
		Size:         len(dataset),
		Schema:       req.Schema,
		DatasetType:  req.DatasetType,
		TargetAction: req.TargetAction,
		MetricRefs:   metricRefs,
		Version:      1,
		CreateTime:   now,
		UpdateTime:   now,
	}
	metadataMap[datasetID] = metadata

	if err := s.writeMetadataMap(metadataMap); err != nil {
		return nil, err
	}
	return &metadata, nil
}

// UpdateDataset merges the provided samples into an existing dataset and bumps
// the dataset version when sample data changes.
func (s *LocalFileDatasetStore) UpdateDataset(req UpdateDatasetRequest) (*DatasetMetadata, error) {
	filePath := s.datasetFilePath(req.DatasetID)
	if _, err := os.Stat(filePath); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, errors.New("update dataset failed: dataset not found")
		}
		return nil, fmt.Errorf("stat dataset: %w", err)
	}

	metadataMap, err := s.readMetadataMap()
	if err != nil {
		return nil, err
	}
	prevMetadata, ok := metadataMap[req.DatasetID]
	if !ok {
		return nil, errors.New("update dataset failed: dataset metadata not found")
	}

	newSize := prevMetadata.Size
	version := prevMetadata.Version
	if req.Data != nil {
		patched, err := s.patchDataset(req.DatasetID, normalizeInferenceDataset(req.Data))
		if err != nil {
			return nil, err
		}
		newSize = len(patched)
		version++
	}

	newMetadata := DatasetMetadata{
		DatasetID:    req.DatasetID,
		Size:         newSize,
		Schema:       firstNonNil(req.Schema, prevMetadata.Schema),
		DatasetType:  prevMetadata.DatasetType,
		TargetAction: firstNonEmpty(req.TargetAction, prevMetadata.TargetAction),
		MetricRefs:   firstNonNilStrings(req.MetricRefs, prevMetadata.MetricRefs),
		Version:      version,
		CreateTime:   prevMetadata.CreateTime,
		UpdateTime:   s.now().String(),
	}
	metadataMap[req.DatasetID] = newMetadata

	if err := s.writeMetadataMap(metadataMap); err != nil {
		return nil, err
	}
	return &newMetadata, nil
}

// GetDataset reads the persisted samples for a dataset ID.
func (s *LocalFileDatasetStore) GetDataset(datasetID string) ([]DatasetSample, error) {
	var dataset []DatasetSample
	if err := readJSONFile(s.datasetFilePath(datasetID), &dataset); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("dataset not found for dataset ID %s", datasetID)
		}
		return nil, fmt.Errorf("read dataset: %w", err)
	}
	return dataset, nil
}

// ListDatasets returns all dataset metadata records sorted by dataset ID.
func (s *LocalFileDatasetStore) ListDatasets() ([]DatasetMetadata, error) {
	metadataMap, err := s.readMetadataMap()
	if err != nil {
		return nil, err
	}

	ids := make([]string, 0, len(metadataMap))
	for datasetID := range metadataMap {
		ids = append(ids, datasetID)
	}
	slices.Sort(ids)

	metadatas := make([]DatasetMetadata, 0, len(ids))
	for _, datasetID := range ids {
		metadatas = append(metadatas, metadataMap[datasetID])
	}
	return metadatas, nil
}

// DeleteDataset removes a dataset file and its metadata entry.
func (s *LocalFileDatasetStore) DeleteDataset(datasetID string) error {
	if err := os.Remove(s.datasetFilePath(datasetID)); err != nil {
		return fmt.Errorf("delete dataset: %w", err)
	}

	metadataMap, err := s.readMetadataMap()
	if err != nil {
		return err
	}
	delete(metadataMap, datasetID)
	return s.writeMetadataMap(metadataMap)
}

func (s *LocalFileDatasetStore) patchDataset(datasetID string, patch []DatasetSample) ([]DatasetSample, error) {
	existing, err := s.GetDataset(datasetID)
	if err != nil {
		return nil, err
	}

	byID := make(map[string]DatasetSample, len(existing))
	order := make([]string, 0, len(existing))
	for _, sample := range existing {
		byID[sample.TestCaseID] = sample
		order = append(order, sample.TestCaseID)
	}

	for _, sample := range patch {
		if _, exists := byID[sample.TestCaseID]; !exists {
			order = append(order, sample.TestCaseID)
		}
		byID[sample.TestCaseID] = sample
	}

	patched := make([]DatasetSample, 0, len(order))
	for _, id := range order {
		patched = append(patched, byID[id])
	}

	if err := writeJSONFile(s.datasetFilePath(datasetID), patched); err != nil {
		return nil, fmt.Errorf("write patched dataset: %w", err)
	}
	return patched, nil
}

func (s *LocalFileDatasetStore) readMetadataMap() (map[string]DatasetMetadata, error) {
	metadataMap := map[string]DatasetMetadata{}
	if err := readJSONFile(s.indexFile, &metadataMap); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return metadataMap, nil
		}
		return nil, fmt.Errorf("read dataset index: %w", err)
	}
	return metadataMap, nil
}

func (s *LocalFileDatasetStore) writeMetadataMap(metadataMap map[string]DatasetMetadata) error {
	if metadataMap == nil {
		metadataMap = map[string]DatasetMetadata{}
	}
	if err := writeJSONFile(s.indexFile, metadataMap); err != nil {
		return fmt.Errorf("write dataset index: %w", err)
	}
	return nil
}

func (s *LocalFileDatasetStore) generateDatasetID(datasetID string, metadataMap map[string]DatasetMetadata) (string, error) {
	if datasetID == "" {
		for {
			candidate := uuid.New().String()
			if _, exists := metadataMap[candidate]; !exists {
				return candidate, nil
			}
		}
	}
	if !datasetIDPattern.MatchString(datasetID) {
		return "", errors.New("invalid datasetId provided. ID must be alphanumeric, with hyphens, dots and dashes. Is must start with an alphabet, end with an alphabet or a number, and must be 6-36 characters long.")
	}
	if _, exists := metadataMap[datasetID]; exists {
		return "", fmt.Errorf("dataset ID not unique: %s", datasetID)
	}
	return datasetID, nil
}

func (s *LocalFileDatasetStore) datasetFilePath(datasetID string) string {
	return filepath.Join(s.storeRoot, datasetID+".json")
}

func normalizeInferenceDataset(data []InferenceSample) []DatasetSample {
	dataset := make([]DatasetSample, 0, len(data))
	for _, sample := range data {
		testCaseID := sample.TestCaseID
		if testCaseID == "" {
			testCaseID = uuid.New().String()
		}
		dataset = append(dataset, DatasetSample{
			TestCaseID: testCaseID,
			Input:      sample.Input,
			Reference:  sample.Reference,
		})
	}
	return dataset
}

func writeJSONFile(path string, value any) error {
	bytes, err := json.Marshal(value)
	if err != nil {
		return err
	}
	return os.WriteFile(path, bytes, 0644)
}

func readJSONFile(path string, dest any) error {
	bytes, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(bytes, dest)
}

func firstNonEmpty(value string, fallback string) string {
	if value != "" {
		return value
	}
	return fallback
}

func firstNonNil[T any](value *T, fallback *T) *T {
	if value != nil {
		return value
	}
	return fallback
}

func firstNonNilStrings(value []string, fallback []string) []string {
	if value != nil {
		return cloneStrings(value)
	}
	return cloneStrings(fallback)
}

func cloneStrings(values []string) []string {
	if len(values) == 0 {
		return []string{}
	}
	return append([]string(nil), values...)
}

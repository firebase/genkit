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

package googlecloud

import (
	"context"
	"log/slog"

	"cloud.google.com/go/logging"
)

// CloudLogger interface for sending structured logs to Google Cloud
// This matches the logger.logStructured() functionality from the TypeScript implementation
type CloudLogger interface {
	LogStructured(ctx context.Context, message string, payload map[string]interface{})
	LogStructuredError(ctx context.Context, message string, payload map[string]interface{})
}

// gcpCloudLogger implements CloudLogger using Google Cloud Logging
type gcpCloudLogger struct {
	logger    *logging.Logger
	projectID string
}

// NewCloudLogger creates a new CloudLogger for Google Cloud Logging
func NewCloudLogger(projectID string) (CloudLogger, error) {
	client, err := logging.NewClient(context.Background(), "projects/"+projectID)
	if err != nil {
		return nil, err
	}

	logger := client.Logger("genkit_log")
	return &gcpCloudLogger{
		logger:    logger,
		projectID: projectID,
	}, nil
}

// LogStructured sends a structured log entry to Google Cloud Logging
// This matches the TypeScript logger.logStructured() functionality
func (c *gcpCloudLogger) LogStructured(ctx context.Context, message string, payload map[string]interface{}) {
	entry := logging.Entry{
		Severity: logging.Info,
		Payload:  payload,
		Labels: map[string]string{
			"module": "genkit",
		},
	}

	// Add the message to the payload
	if payload == nil {
		payload = make(map[string]interface{})
	}
	payload["message"] = message
	entry.Payload = payload

	c.logger.Log(entry)
}

// LogStructuredError sends a structured error log entry to Google Cloud Logging
func (c *gcpCloudLogger) LogStructuredError(ctx context.Context, message string, payload map[string]interface{}) {
	entry := logging.Entry{
		Severity: logging.Error,
		Payload:  payload,
		Labels: map[string]string{
			"module": "genkit",
		},
	}

	// Add the message to the payload
	if payload == nil {
		payload = make(map[string]interface{})
	}
	payload["message"] = message
	entry.Payload = payload

	c.logger.Log(entry)
}

// noOpCloudLogger is a no-op implementation for when Cloud Logging is disabled
type noOpCloudLogger struct{}

func (n *noOpCloudLogger) LogStructured(ctx context.Context, message string, payload map[string]interface{}) {
	// Log to local slog for debugging but don't send to Cloud
	slog.Debug("CloudLogger (no-op)", "message", message, "payload", payload)
}

func (n *noOpCloudLogger) LogStructuredError(ctx context.Context, message string, payload map[string]interface{}) {
	// Log to local slog for debugging but don't send to Cloud
	slog.Debug("CloudLogger (no-op error)", "message", message, "payload", payload)
}

// NewNoOpCloudLogger creates a no-op CloudLogger for when Cloud Logging is disabled
func NewNoOpCloudLogger() CloudLogger {
	return &noOpCloudLogger{}
}

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

// The googlecloud package supports telemetry (tracing, metrics and logging) using
// Google Cloud services.
package googlecloud

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"sync"
	"time"

	"cloud.google.com/go/logging"
	"github.com/jba/slog/withsupport"
	"go.opentelemetry.io/otel/trace"
)

// Enhanced handler with error handling and recovery capabilities
type handler struct {
	level              slog.Leveler
	handleEntry        func(logging.Entry)
	goa                *withsupport.GroupOrAttrs
	projectID          string
	fallbackHandler    slog.Handler
	instructionsLogged bool
	instructionsMutex  sync.Mutex
	recoveryInProgress bool
	recoveryMutex      sync.Mutex
}

func newHandler(level slog.Leveler, f func(logging.Entry), projectID string) *handler {
	if level == nil {
		level = slog.LevelInfo
	}

	// Create fallback handler for when GCP logging fails
	fallbackHandler := slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
		Level: level,
	})

	return &handler{
		level:              level,
		handleEntry:        f,
		projectID:          projectID,
		fallbackHandler:    fallbackHandler,
		instructionsLogged: false,
		recoveryInProgress: false,
	}
}

func (h *handler) Enabled(ctx context.Context, level slog.Level) bool {
	return level >= h.level.Level()
}

func (h *handler) WithAttrs(as []slog.Attr) slog.Handler {
	return &handler{
		level:              h.level,
		handleEntry:        h.handleEntry,
		goa:                h.goa.WithAttrs(as),
		projectID:          h.projectID,
		fallbackHandler:    h.fallbackHandler,
		instructionsLogged: false,
		recoveryInProgress: false,
	}
}

func (h *handler) WithGroup(name string) slog.Handler {
	return &handler{
		level:              h.level,
		handleEntry:        h.handleEntry,
		goa:                h.goa.WithGroup(name),
		projectID:          h.projectID,
		fallbackHandler:    h.fallbackHandler,
		instructionsLogged: false,
		recoveryInProgress: false,
	}
}

func (h *handler) Handle(ctx context.Context, r slog.Record) error {
	entry := h.recordToEntry(ctx, r)

	// Try to send to GCP with error handling and recovery
	if err := h.handleWithRecovery(entry); err != nil {
		// Fall back to local logging if GCP fails
		return h.fallbackHandler.Handle(ctx, r)
	}

	return nil
}

// handleWithRecovery attempts to send the log entry to GCP
func (h *handler) handleWithRecovery(entry logging.Entry) error {
	// Attempt to send the log entry
	defer func() {
		if r := recover(); r != nil {
			// Handle panics gracefully and trigger immediate recovery
			h.handleError(fmt.Errorf("panic in GCP logging: %v", r))
		}
	}()

	// Create a channel to capture any errors from the async logging operation
	errChan := make(chan error, 1)

	// Wrap the handleEntry function to capture errors
	wrappedHandleEntry := func(entry logging.Entry) {
		defer func() {
			if r := recover(); r != nil {
				errChan <- fmt.Errorf("logging operation panic: %v", r)
			} else {
				errChan <- nil
			}
		}()
		h.handleEntry(entry)
	}

	// Execute the logging operation
	go wrappedHandleEntry(entry)

	// Wait for completion with timeout
	select {
	case err := <-errChan:
		if err != nil {
			h.handleError(err)
			return err
		}
		return nil
	case <-time.After(5 * time.Second):
		err := fmt.Errorf("GCP logging timeout")
		h.handleError(err)
		return err
	}
}

// handleError processes logging errors and triggers immediate recovery
func (h *handler) handleError(err error) {
	// Check if this is a permission denied error for helpful messaging
	if loggingDenied(err) {
		h.logPermissionError(err)
	} else {
		// Log generic error
		h.fallbackHandler.Handle(context.Background(), slog.NewRecord(
			time.Now(),
			slog.LevelError,
			fmt.Sprintf("Unable to send logs to Google Cloud: %v", err),
			0,
		))
	}

	// Attempt immediate recovery
	go h.attemptRecovery()
}

// logPermissionError logs helpful permission error messages (only once)
func (h *handler) logPermissionError(err error) {
	h.instructionsMutex.Lock()
	defer h.instructionsMutex.Unlock()

	if !h.instructionsLogged {
		h.instructionsLogged = true
		helpText := loggingDeniedHelpText(h.projectID)

		errorMsg := fmt.Sprintf("Unable to send logs to Google Cloud: %v\n\n%s\n", err, helpText)

		h.fallbackHandler.Handle(context.Background(), slog.NewRecord(
			time.Now(),
			slog.LevelError,
			errorMsg,
			0,
		))
	}
}

// attemptRecovery tries to reinitialize the logging connection immediately
func (h *handler) attemptRecovery() {
	h.recoveryMutex.Lock()
	defer h.recoveryMutex.Unlock()

	if h.recoveryInProgress {
		return
	}

	h.recoveryInProgress = true
	defer func() { h.recoveryInProgress = false }()

	// Try to create a new logging client immediately
	newClient, err := logging.NewClient(context.Background(), "projects/"+h.projectID)
	if err != nil {
		// Log failure but don't retry
		h.fallbackHandler.Handle(context.Background(), slog.NewRecord(
			time.Now(),
			slog.LevelWarn,
			fmt.Sprintf("Failed to recover GCP logging connection: %v", err),
			0,
		))
		return
	}

	// Successfully recovered - update handler
	h.handleEntry = newClient.Logger("genkit_log").Log
	h.instructionsLogged = false // Allow instructions to be shown again if needed

	h.fallbackHandler.Handle(context.Background(), slog.NewRecord(
		time.Now(),
		slog.LevelInfo,
		"Successfully recovered GCP logging connection",
		0,
	))
}

func (h *handler) recordToEntry(ctx context.Context, r slog.Record) logging.Entry {
	span := trace.SpanFromContext(ctx)

	entry := logging.Entry{
		Timestamp: r.Time,
		Severity:  levelToSeverity(r.Level),
		Payload:   recordToMap(r, h.goa.Collect()),
		Labels:    map[string]string{"module": "genkit"},
	}

	// Add trace context if span is valid
	if span.SpanContext().IsValid() {
		entry.Trace = fmt.Sprintf("projects/%s/traces/%s", h.projectID, span.SpanContext().TraceID().String())
		entry.SpanID = span.SpanContext().SpanID().String()
		entry.TraceSampled = span.SpanContext().IsSampled()
	}

	return entry
}

func levelToSeverity(l slog.Level) logging.Severity {
	switch {
	case l < slog.LevelInfo:
		return logging.Debug
	case l == slog.LevelInfo:
		return logging.Info
	case l < slog.LevelWarn:
		return logging.Notice
	case l < slog.LevelError:
		return logging.Warning
	case l == slog.LevelError:
		return logging.Error
	case l <= slog.LevelError+4:
		return logging.Critical
	case l <= slog.LevelError+8:
		return logging.Alert
	default:
		return logging.Emergency
	}
}

func recordToMap(r slog.Record, goras []*withsupport.GroupOrAttrs) map[string]any {
	root := map[string]any{}
	root[slog.MessageKey] = r.Message

	m := root
	for i, gora := range goras {
		if gora.Group != "" {
			if i == len(goras)-1 && r.NumAttrs() == 0 {
				continue
			}
			m2 := map[string]any{}
			m[gora.Group] = m2
			m = m2
		} else {
			for _, a := range gora.Attrs {
				handleAttr(a, m)
			}
		}
	}
	r.Attrs(func(a slog.Attr) bool {
		handleAttr(a, m)
		return true
	})
	return root
}

func handleAttr(a slog.Attr, m map[string]any) {
	if a.Equal(slog.Attr{}) {
		return
	}
	v := a.Value.Resolve()
	if v.Kind() == slog.KindGroup {
		gas := v.Group()
		if len(gas) == 0 {
			return
		}
		if a.Key == "" {
			for _, ga := range gas {
				handleAttr(ga, m)
			}
		} else {
			gm := map[string]any{}
			for _, ga := range gas {
				handleAttr(ga, gm)
			}
			m[a.Key] = gm
		}
	} else {
		m[a.Key] = v.Any()
	}
}

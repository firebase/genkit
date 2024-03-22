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

// This file implements a server used for development.
// The genkit CLI sends requests to it.
//
// See js/common/src/reflectionApi.ts.

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net/http"
	"strconv"
	"sync/atomic"

	"go.opentelemetry.io/otel/trace"
)

// StartDevServer starts the development server (reflection API) at the given address.
// If addr is empty, it uses port 3100.
// StartDevServer always returns a non-nil error, the one returned by http.ListenAndServe.
func StartDevServer(addr string) error {
	if addr == "" {
		addr = "localhost:3100"
	}
	mux := newDevServerMux()
	slog.Info("listening", "addr", addr)
	return http.ListenAndServe(addr, mux)
}

func newDevServerMux() *http.ServeMux {
	mux := http.NewServeMux()
	handle(mux, "POST /api/runAction", handleRunAction)
	handle(mux, "GET /api/actions", handleListActions)
	handle(mux, "GET /api/envs/{env}/traces/{traceID}", handleGetTrace)
	handle(mux, "GET /api/envs/{env}/traces", handleListTraces)
	return mux
}

// requestID is a unique ID for each request.
var requestID atomic.Int64

// handle registers pattern on mux with an http.Handler that calls f.
// If f returns a non-nil error, the handler calls http.Error.
// If the error is an httpError, the code it contains is used as the status code;
// otherwise a 500 status is used.
func handle(mux *http.ServeMux, pattern string, f func(w http.ResponseWriter, r *http.Request) error) {
	mux.HandleFunc(pattern, func(w http.ResponseWriter, r *http.Request) {
		id := requestID.Add(1)
		// Create a logger that always outputs the requestID, and store it in the request context.
		log := slog.Default().With("reqID", id)
		log.Info("request start",
			"method", r.Method,
			"path", r.URL.Path)
		var err error
		defer func() {
			if err != nil {
				log.Error("request end", "err", err)
			} else {
				log.Info("request end")
			}
		}()
		err = f(w, r)
		if err != nil {
			// If the error is an httpError, serve the status code it contains.
			// Otherwise, assume this is an unexpected error and serve a 500.
			var herr *httpError
			if errors.As(err, &herr) {
				http.Error(w, herr.Error(), herr.code)
			} else {
				http.Error(w, err.Error(), http.StatusInternalServerError)
			}
		}
	})
}

type httpError struct {
	code int
	err  error
}

func (e *httpError) Error() string {
	return fmt.Sprintf("%s: %s", http.StatusText(e.code), e.err)
}

// handleRunAction looks up an action by name in the registry, runs it with the
// provded JSON input, and writes back the JSON-marshaled request.
func handleRunAction(w http.ResponseWriter, r *http.Request) error {
	ctx := r.Context()
	var body struct {
		Key   string          `json:"key"`
		Input json.RawMessage `json:"input"`
	}
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		return &httpError{http.StatusBadRequest, err}
	}
	action := lookupAction(body.Key)
	logger(ctx).Debug("running action", "key", body.Key)
	if action == nil {
		return &httpError{http.StatusNotFound, fmt.Errorf("no action with key %q", body.Key)}
	}
	var traceID string
	output, err := runInNewSpan(ctx, "dev-run-action-wrapper", "", body.Input, func(ctx context.Context, input json.RawMessage) ([]byte, error) {
		setCustomMetadataAttr(ctx, "genkit-dev-internal", "true")
		traceID = trace.SpanContextFromContext(ctx).TraceID().String()
		return action.runJSON(ctx, input)
	})
	if err != nil {
		return err
	}
	return writeJSON(ctx, w, runActionResponse{
		Result:    output,
		Telemetry: telemetry{TraceID: traceID},
	})
}

type runActionResponse struct {
	Result    json.RawMessage `json:"result"`
	Telemetry telemetry       `json:"telemetry"`
}

type telemetry struct {
	TraceID string `json:"traceId"`
}

// handleListActions lists all the registered actions.
func handleListActions(w http.ResponseWriter, r *http.Request) error {
	descs := listActions()
	return writeJSON(r.Context(), w, descs)
}

// handleGetTrace returns a single trace from a TraceStore.
func handleGetTrace(w http.ResponseWriter, r *http.Request) error {
	env := r.PathValue("env")
	ts := lookupTraceStore(Environment(env))
	if ts == nil {
		return &httpError{http.StatusNotFound, fmt.Errorf("no TraceStore for environment %q", env)}
	}
	tid := r.PathValue("traceID")
	td, err := ts.Load(r.Context(), tid)
	if errors.Is(err, fs.ErrNotExist) {
		return &httpError{http.StatusNotFound, fmt.Errorf("no %s trace with ID %q", env, tid)}
	}
	if err != nil {
		return err
	}
	return writeJSON(r.Context(), w, td)
}

// handleListTraces returns a list of traces from a TraceStore.
func handleListTraces(w http.ResponseWriter, r *http.Request) error {
	env := r.PathValue("env")
	ts := lookupTraceStore(Environment(env))
	if ts == nil {
		return &httpError{http.StatusNotFound, fmt.Errorf("no TraceStore for environment %q", env)}
	}
	limit := 0
	if lim := r.FormValue("limit"); lim != "" {
		var err error
		limit, err = strconv.Atoi(lim)
		if err != nil {
			return &httpError{http.StatusBadRequest, err}
		}
	}
	ctoken := r.FormValue("continuationToken")
	tds, ctoken, err := ts.List(r.Context(), &TraceQuery{Limit: limit, ContinuationToken: ctoken})
	if errors.Is(err, errBadQuery) {
		return &httpError{http.StatusBadRequest, err}
	}
	if err != nil {
		return err
	}
	return writeJSON(r.Context(), w, listTracesResult{tds, ctoken})
}

type listTracesResult struct {
	Traces            []*TraceData `json:"traces"`
	ContinuationToken string       `json:"continuationToken"`
}

func writeJSON(ctx context.Context, w http.ResponseWriter, value any) error {
	data, err := json.MarshalIndent(value, "", "    ")
	if err != nil {
		return err
	}
	_, err = w.Write(data)
	if err != nil {
		logger(ctx).Error("writing output", "err", err)
	}
	return nil
}

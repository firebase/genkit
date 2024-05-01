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
	"os"
	"os/signal"
	"strconv"
	"sync/atomic"
	"syscall"
	"time"

	"go.opentelemetry.io/otel/trace"
)

// StartDevServer starts the development server (reflection API) listening at the given address.
// If addr is "", it uses ":3100".
// StartDevServer always returns a non-nil error, the one returned by http.ListenAndServe.
func StartDevServer(addr string) error {
	mux := newDevServerMux(globalRegistry)
	if addr == "" {
		port := os.Getenv("GENKIT_REFLECTION_PORT")
		if port != "" {
			addr = ":" + port
		} else {
			// Don't use "localhost" here. That only binds the IPv4 address, and the genkit tool
			// wants to connect to the IPv6 address even when you tell it to use "localhost".
			// Omitting the host works.
			addr = ":3100"
		}
	}
	server := &http.Server{
		Addr:    addr,
		Handler: mux,
	}
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGTERM)
	go func() {
		<-sigCh
		slog.Info("received SIGTERM, shutting down server")
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := server.Shutdown(ctx); err != nil {
			slog.Error("server shutdown failed", "err", err)
		} else {
			slog.Info("server shutdown successfully")
		}
	}()
	slog.Info("listening", "addr", addr)
	return server.ListenAndServe()
}

type devServer struct {
	reg *registry
}

func newDevServerMux(r *registry) *http.ServeMux {
	mux := http.NewServeMux()
	s := &devServer{r}
	handle(mux, "GET /api/__health", func(w http.ResponseWriter, _ *http.Request) error {
		return nil
	})
	handle(mux, "POST /api/runAction", s.handleRunAction)
	handle(mux, "GET /api/actions", s.handleListActions)
	handle(mux, "GET /api/envs/{env}/traces/{traceID}", s.handleGetTrace)
	handle(mux, "GET /api/envs/{env}/traces", s.handleListTraces)
	handle(mux, "GET /api/envs/{env}/flowStates", s.handleListFlowStates)

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
func (s *devServer) handleRunAction(w http.ResponseWriter, r *http.Request) error {
	ctx := r.Context()
	var body struct {
		Key   string          `json:"key"`
		Input json.RawMessage `json:"input"`
	}
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		return &httpError{http.StatusBadRequest, err}
	}
	stream := false
	if s := r.FormValue("stream"); s != "" {
		var err error
		stream, err = strconv.ParseBool(s)
		if err != nil {
			return err
		}
	}
	logger(ctx).Debug("running action",
		"key", body.Key,
		"stream", stream)
	var callback StreamingCallback[json.RawMessage]
	if stream {
		// Stream results are newline-separated JSON.
		callback = func(ctx context.Context, msg json.RawMessage) error {
			_, err := fmt.Fprintf(w, "%s\n", msg)
			return err
		}
	}
	resp, err := runAction(ctx, s.reg, body.Key, body.Input, callback)
	if err != nil {
		return err
	}
	return writeJSON(ctx, w, resp)
}

type runActionResponse struct {
	Result    json.RawMessage `json:"result"`
	Telemetry telemetry       `json:"telemetry"`
}

type telemetry struct {
	TraceID string `json:"traceId"`
}

func runAction(ctx context.Context, reg *registry, key string, input json.RawMessage, cb StreamingCallback[json.RawMessage]) (*runActionResponse, error) {
	action := reg.lookupAction(key)
	if action == nil {
		return nil, &httpError{http.StatusNotFound, fmt.Errorf("no action with key %q", key)}
	}
	var traceID string
	output, err := runInNewSpan(ctx, reg.tstate, "dev-run-action-wrapper", "", true, input, func(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
		SetCustomMetadataAttr(ctx, "genkit-dev-internal", "true")
		traceID = trace.SpanContextFromContext(ctx).TraceID().String()
		return action.runJSON(ctx, input, cb)
	})
	if err != nil {
		return nil, err
	}
	return &runActionResponse{
		Result:    output,
		Telemetry: telemetry{TraceID: traceID},
	}, nil
}

// handleListActions lists all the registered actions.
func (s *devServer) handleListActions(w http.ResponseWriter, r *http.Request) error {
	descs := s.reg.listActions()
	descMap := map[string]actionDesc{}
	for _, d := range descs {
		descMap[d.Key] = d
	}
	return writeJSON(r.Context(), w, descMap)
}

// handleGetTrace returns a single trace from a TraceStore.
func (s *devServer) handleGetTrace(w http.ResponseWriter, r *http.Request) error {
	env := r.PathValue("env")
	ts := s.reg.lookupTraceStore(Environment(env))
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
func (s *devServer) handleListTraces(w http.ResponseWriter, r *http.Request) error {
	env := r.PathValue("env")
	ts := s.reg.lookupTraceStore(Environment(env))
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
	if tds == nil {
		tds = []*TraceData{}
	}
	return writeJSON(r.Context(), w, listTracesResult{tds, ctoken})
}

type listTracesResult struct {
	Traces            []*TraceData `json:"traces"`
	ContinuationToken string       `json:"continuationToken"`
}

func (s *devServer) handleListFlowStates(w http.ResponseWriter, r *http.Request) error {
	// TODO(jba): implement.
	return writeJSON(r.Context(), w, listFlowStatesResult{[]flowStater{}, ""})
}

type listFlowStatesResult struct {
	FlowStates        []flowStater `json:"flowStates"`
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

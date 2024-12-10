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

// This file implements production and development servers.
//
// The genkit CLI sends requests to the development server.
// See js/common/src/reflectionApi.ts.
//
// The production server has a route for each flow. It
// is intended for production deployments.

package genkit

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"sync/atomic"
	"time"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
	"go.opentelemetry.io/otel/trace"
)

type runtimeFileData struct {
	ID                       string `json:"id"`
	PID                      int    `json:"pid"`
	ReflectionServerURL      string `json:"reflectionServerUrl"`
	Timestamp                string `json:"timestamp"`
	GenkitVersion            string `json:"genkitVersion"`
	ReflectionApiSpecVersion int    `json:"reflectionApiSpecVersion"`
}

type devServer struct {
	reg             *registry.Registry
	runtimeFilePath string
}

// startReflectionServer starts the Reflection API server listening at the
// value of the environment variable GENKIT_REFLECTION_PORT for the port,
// or ":3100" if it is empty.
func startReflectionServer(ctx context.Context, errCh chan<- error) *http.Server {
	slog.Debug("starting reflection server")
	addr := serverAddress("", "GENKIT_REFLECTION_PORT", "127.0.0.1:3100")
	s := &devServer{reg: registry.Global}
	if err := s.writeRuntimeFile(addr); err != nil {
		slog.Error("failed to write runtime file", "error", err)
	}
	mux := newDevServeMux(s)
	server := startServer(addr, mux, errCh)
	go func() {
		<-ctx.Done()
		if err := s.cleanupRuntimeFile(); err != nil {
			slog.Error("failed to cleanup runtime file", "error", err)
		}
	}()
	return server
}

// writeRuntimeFile writes a file describing the runtime to the project root.
func (s *devServer) writeRuntimeFile(url string) error {
	projectRoot, err := findProjectRoot()
	if err != nil {
		return fmt.Errorf("failed to find project root: %w", err)
	}
	runtimesDir := filepath.Join(projectRoot, ".genkit", "runtimes")
	if err := os.MkdirAll(runtimesDir, 0755); err != nil {
		return fmt.Errorf("failed to create runtimes directory: %w", err)
	}
	runtimeID := os.Getenv("GENKIT_RUNTIME_ID")
	if runtimeID == "" {
		runtimeID = strconv.Itoa(os.Getpid())
	}
	timestamp := time.Now().UTC().Format(time.RFC3339)
	s.runtimeFilePath = filepath.Join(runtimesDir, fmt.Sprintf("%d-%s.json", os.Getpid(), timestamp))
	data := runtimeFileData{
		ID:                       runtimeID,
		PID:                      os.Getpid(),
		ReflectionServerURL:      fmt.Sprintf("http://%s", url),
		Timestamp:                timestamp,
		GenkitVersion:            "go/" + internal.Version,
		ReflectionApiSpecVersion: internal.GENKIT_REFLECTION_API_SPEC_VERSION,
	}
	fileContent, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal runtime data: %w", err)
	}
	if err := os.WriteFile(s.runtimeFilePath, fileContent, 0644); err != nil {
		return fmt.Errorf("failed to write runtime file: %w", err)
	}
	slog.Debug("runtime file written", "path", s.runtimeFilePath)
	return nil
}

// cleanupRuntimeFile removes the runtime file associated with the dev server.
func (s *devServer) cleanupRuntimeFile() error {
	if s.runtimeFilePath == "" {
		return nil
	}
	content, err := os.ReadFile(s.runtimeFilePath)
	if err != nil {
		return fmt.Errorf("failed to read runtime file: %w", err)
	}
	var data runtimeFileData
	if err := json.Unmarshal(content, &data); err != nil {
		return fmt.Errorf("failed to unmarshal runtime data: %w", err)
	}
	if data.PID == os.Getpid() {
		if err := os.Remove(s.runtimeFilePath); err != nil {
			return fmt.Errorf("failed to remove runtime file: %w", err)
		}
		slog.Debug("runtime file cleaned up", "path", s.runtimeFilePath)
	}
	return nil
}

// findProjectRoot finds the project root by looking for a go.mod file.
func findProjectRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("could not find project root (go.mod not found)")
		}
		dir = parent
	}
}

// startFlowServer starts a production server listening at the given address.
// The Server has a route for each defined flow.
// If addr is "", it uses the value of the environment variable PORT
// for the port, and if that is empty it uses ":3400".
//
// To construct a server with additional routes, use [NewFlowServeMux].
func startFlowServer(addr string, flows []string, errCh chan<- error) *http.Server {
	slog.Debug("starting flow server")
	addr = serverAddress(addr, "PORT", "127.0.0.1:3400")
	mux := NewFlowServeMux(flows)
	return startServer(addr, mux, errCh)
}

// flow is the type that all Flow[In, Out, Stream] have in common.
type flow interface {
	Name() string

	// runJSON uses encoding/json to unmarshal the input,
	// calls Flow.start, then returns the marshaled result.
	runJSON(ctx context.Context, authHeader string, input json.RawMessage, cb streamingCallback[json.RawMessage]) (json.RawMessage, error)
}

// startServer starts an HTTP server listening on the address.
// It returns the server an
func startServer(addr string, handler http.Handler, errCh chan<- error) *http.Server {
	server := &http.Server{
		Addr:    addr,
		Handler: handler,
	}

	go func() {
		slog.Debug("server listening", "addr", addr)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errCh <- fmt.Errorf("server error on %s: %w", addr, err)
		}
	}()

	return server
}

// shutdownServers initiates shutdown of the servers and waits for the shutdown to complete.
// After 5 seconds, it will timeout.
func shutdownServers(servers []*http.Server) error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var wg sync.WaitGroup
	for _, server := range servers {
		wg.Add(1)
		go func(srv *http.Server) {
			defer wg.Done()
			if err := srv.Shutdown(ctx); err != nil {
				slog.Error("server shutdown failed", "addr", srv.Addr, "err", err)
			} else {
				slog.Debug("server shutdown successfully", "addr", srv.Addr)
			}
		}(server)
	}

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		slog.Info("all servers shut down successfully")
	case <-ctx.Done():
		return errors.New("server shutdown timed out")
	}

	return nil
}

func newDevServeMux(s *devServer) *http.ServeMux {
	mux := http.NewServeMux()
	handle(mux, "GET /api/__health", func(w http.ResponseWriter, _ *http.Request) error {
		return nil
	})
	handle(mux, "POST /api/runAction", s.handleRunAction)
	handle(mux, "GET /api/actions", s.handleListActions)
	handle(mux, "POST /api/notify", s.handleNotify)
	return mux
}

// handleRunAction looks up an action by name in the registry, runs it with the
// provided JSON input, and writes back the JSON-marshaled request.
func (s *devServer) handleRunAction(w http.ResponseWriter, r *http.Request) error {
	ctx := r.Context()
	var body struct {
		Key     string          `json:"key"`
		Input   json.RawMessage `json:"input"`
		Context json.RawMessage `json:"context"`
	}
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		return &base.HTTPError{Code: http.StatusBadRequest, Err: err}
	}
	stream, err := parseBoolQueryParam(r, "stream")
	if err != nil {
		return err
	}
	logger.FromContext(ctx).Debug("running action",
		"key", body.Key,
		"stream", stream)
	var callback streamingCallback[json.RawMessage]
	if stream {
		w.Header().Set("Content-Type", "text/plain")
		w.Header().Set("Transfer-Encoding", "chunked")
		// Stream results are newline-separated JSON.
		callback = func(ctx context.Context, msg json.RawMessage) error {
			_, err := fmt.Fprintf(w, "%s\n", msg)
			if err != nil {
				return err
			}
			if f, ok := w.(http.Flusher); ok {
				f.Flush()
			}
			return nil
		}
	}
	var contextMap map[string]any = nil
	if body.Context != nil {
		json.Unmarshal(body.Context, &contextMap)
	}
	resp, err := runAction(ctx, s.reg, body.Key, body.Input, callback, contextMap)
	if err != nil {
		return err
	}
	return writeJSON(ctx, w, resp)
}

// handleNotify configures the telemetry server URL from the request.
func (s *devServer) handleNotify(w http.ResponseWriter, r *http.Request) error {
	var body struct {
		TelemetryServerURL       string `json:"telemetryServerUrl"`
		ReflectionApiSpecVersion int    `json:"reflectionApiSpecVersion"`
	}
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		return &base.HTTPError{Code: http.StatusBadRequest, Err: err}
	}
	if body.TelemetryServerURL != "" {
		s.reg.TracingState().WriteTelemetryImmediate(tracing.NewHTTPTelemetryClient(body.TelemetryServerURL))
		slog.Debug("connected to telemetry server", "url", body.TelemetryServerURL)
	}
	if body.ReflectionApiSpecVersion != internal.GENKIT_REFLECTION_API_SPEC_VERSION {
		slog.Error("Genkit CLI version is not compatible with runtime library. Please use `genkit-cli` version compatible with runtime library version.")
	}
	w.WriteHeader(http.StatusOK)
	_, err := w.Write([]byte("OK"))
	return err
}

type runActionResponse struct {
	Result    json.RawMessage `json:"result"`
	Telemetry telemetry       `json:"telemetry"`
}

type telemetry struct {
	TraceID string `json:"traceId"`
}

func runAction(ctx context.Context, reg *registry.Registry, key string, input json.RawMessage, cb streamingCallback[json.RawMessage], runtimeContext map[string]any) (*runActionResponse, error) {
	action := reg.LookupAction(key)
	if action == nil {
		return nil, &base.HTTPError{Code: http.StatusNotFound, Err: fmt.Errorf("no action with key %q", key)}
	}
	if runtimeContext != nil {
		ctx = core.WithActionContext(ctx, runtimeContext)
	}

	var traceID string
	output, err := tracing.RunInNewSpan(ctx, reg.TracingState(), "dev-run-action-wrapper", "", true, input, func(ctx context.Context, input json.RawMessage) (json.RawMessage, error) {
		tracing.SetCustomMetadataAttr(ctx, "genkit-dev-internal", "true")
		traceID = trace.SpanContextFromContext(ctx).TraceID().String()
		return action.RunJSON(ctx, input, cb)
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
	descs := s.reg.ListActions()
	descMap := map[string]action.Desc{}
	for _, d := range descs {
		descMap[d.Key] = d
	}
	return writeJSON(r.Context(), w, descMap)
}

// NewFlowServeMux constructs a [net/http.ServeMux].
// If flows is non-empty, the each of the named flows is registered as a route.
// Otherwise, all defined flows are registered.
//
// All routes take a single query parameter, "stream", which if true will stream the
// flow's results back to the client. (Not all flows support streaming, however.)
//
// To use the returned ServeMux as part of a server with other routes, either add routes
// to it, or install it as part of another ServeMux, like so:
//
//	mainMux := http.NewServeMux()
//	mainMux.Handle("POST /flow/", http.StripPrefix("/flow/", NewFlowServeMux()))
func NewFlowServeMux(flows []string) *http.ServeMux {
	return newFlowServeMux(registry.Global, flows)
}

func newFlowServeMux(r *registry.Registry, flows []string) *http.ServeMux {
	mux := http.NewServeMux()
	m := map[string]bool{}
	for _, f := range flows {
		m[f] = true
	}
	for _, f := range r.ListFlows() {
		f := f.(flow)
		if len(flows) == 0 || m[f.Name()] {
			handle(mux, "POST /"+f.Name(), nonDurableFlowHandler(f))
		}
	}
	return mux
}

func nonDurableFlowHandler(f flow) func(http.ResponseWriter, *http.Request) error {
	return func(w http.ResponseWriter, r *http.Request) error {
		var body struct {
			Data json.RawMessage `json:"data"`
		}
		defer r.Body.Close()
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			return &base.HTTPError{Code: http.StatusBadRequest, Err: err}
		}
		stream, err := parseBoolQueryParam(r, "stream")
		if err != nil {
			return err
		}
		var callback streamingCallback[json.RawMessage]
		if r.Header.Get("Accept") == "text/event-stream" || stream {
			w.Header().Set("Content-Type", "text/plain")
			w.Header().Set("Transfer-Encoding", "chunked")
			// Event Stream results are in JSON format separated by two newline escape sequences
			// including the `data` and `message` labels
			callback = func(ctx context.Context, msg json.RawMessage) error {
				_, err := fmt.Fprintf(w, "data: {\"message\": %s}\n\n", msg)
				if err != nil {
					return err
				}
				if f, ok := w.(http.Flusher); ok {
					f.Flush()
				}
				return nil
			}
		}
		// TODO: telemetry
		out, err := f.runJSON(r.Context(), r.Header.Get("Authorization"), body.Data, callback)
		if err != nil {
			if r.Header.Get("Accept") == "text/event-stream" || stream {
				_, err = fmt.Fprintf(w, "data: {\"error\": {\"status\": \"INTERNAL\", \"message\": \"stream flow error\", \"details\": \"%v\"}}\n\n", err)
				return err
			}
			return err
		}
		// Responses for streaming, non-durable flows should be prefixed
		// with "data"
		if r.Header.Get("Accept") == "text/event-stream" || stream {
			_, err = fmt.Fprintf(w, "data: {\"result\": %s}\n\n", out)
			return err
		}

		// Responses for non-streaming, non-durable flows are passed back
		// with the flow result stored in a field called "result."
		_, err = fmt.Fprintf(w, `{"result": %s}\n`, out)
		return err
	}
}

// serverAddress determines a server address.
func serverAddress(arg, envVar, defaultValue string) string {
	if arg != "" {
		return arg
	}
	if port := os.Getenv(envVar); port != "" {
		return "127.0.0.1:" + port
	}
	return defaultValue
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
			var herr *base.HTTPError
			if errors.As(err, &herr) {
				http.Error(w, herr.Error(), herr.Code)
			} else {
				http.Error(w, err.Error(), http.StatusInternalServerError)
			}
		}
	})
}

func parseBoolQueryParam(r *http.Request, name string) (bool, error) {
	b := false
	if s := r.FormValue(name); s != "" {
		var err error
		b, err = strconv.ParseBool(s)
		if err != nil {
			return false, &base.HTTPError{Code: http.StatusBadRequest, Err: err}
		}
	}
	return b, nil
}

func writeJSON(ctx context.Context, w http.ResponseWriter, value any) error {
	data, err := json.Marshal(value)
	if err != nil {
		return err
	}
	_, err = w.Write(data)
	if err != nil {
		logger.FromContext(ctx).Error("writing output", "err", err)
	}
	if f, ok := w.(http.Flusher); ok {
		f.Flush()
	}
	return nil
}

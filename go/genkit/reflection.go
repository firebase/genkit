// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package genkit

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
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

type streamingCallback[Stream any] = func(context.Context, Stream) error

// runtimeFileData is the data written to the file describing this runtime.
type runtimeFileData struct {
	ID                       string `json:"id"`
	PID                      int    `json:"pid"`
	ReflectionServerURL      string `json:"reflectionServerUrl"`
	Timestamp                string `json:"timestamp"`
	GenkitVersion            string `json:"genkitVersion"`
	ReflectionApiSpecVersion int    `json:"reflectionApiSpecVersion"`
}

// reflectionServer encapsulates everything needed to serve the Reflection API.
type reflectionServer struct {
	*http.Server
	Reg             *registry.Registry // Registry from which the server gets its actions.
	RuntimeFilePath string             // Path to the runtime file that was written at startup.
}

// startReflectionServer starts the Reflection API server listening at the
// value of the environment variable GENKIT_REFLECTION_PORT for the port,
// or ":3100" if it is empty.
func startReflectionServer(ctx context.Context, r *registry.Registry, errCh chan<- error, serverStartCh chan<- struct{}) *reflectionServer {
	if r == nil {
		errCh <- fmt.Errorf("nil registry provided")
		return nil
	}

	addr := "127.0.0.1:3100"
	if os.Getenv("GENKIT_REFLECTION_PORT") != "" {
		addr = "127.0.0.1:" + os.Getenv("GENKIT_REFLECTION_PORT")
	}

	s := &reflectionServer{
		Server: &http.Server{
			Addr:    addr,
			Handler: serveMux(r),
		},
		Reg: r,
	}

	slog.Debug("starting reflection server", "addr", s.Addr)

	if err := s.writeRuntimeFile(s.Addr); err != nil {
		errCh <- fmt.Errorf("failed to write runtime file: %w", err)
		return nil
	}

	serverCtx, cancel := context.WithCancel(context.Background())

	go func() {
		// First check that the port is available before signaling a server start success.
		listener, err := net.Listen("tcp", s.Addr)
		if err != nil {
			errCh <- fmt.Errorf("failed to create listener: %w", err)
			return
		}

		close(serverStartCh)

		if err := s.Serve(listener); err != nil && err != http.ErrServerClosed {
			errCh <- err
		}
		// If the server shuts down unexpectedly, this will trigger the cleanup.
		cancel()
	}()

	go func() {
		// Blocks here until the context is done or the server crashes.
		select {
		case <-ctx.Done():
		case <-serverCtx.Done():
			return
		}

		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err := s.Shutdown(shutdownCtx); err != nil {
			slog.Error("reflection server shutdown error", "error", err)
		}

		if err := s.cleanupRuntimeFile(); err != nil {
			slog.Error("failed to cleanup runtime file", "error", err)
		}
	}()

	return s
}

// writeRuntimeFile writes a file describing the runtime to the project root.
func (s *reflectionServer) writeRuntimeFile(url string) error {
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
	s.RuntimeFilePath = filepath.Join(runtimesDir, fmt.Sprintf("%d-%s.json", os.Getpid(), timestamp))

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

	if err := os.WriteFile(s.RuntimeFilePath, fileContent, 0644); err != nil {
		return fmt.Errorf("failed to write runtime file: %w", err)
	}

	slog.Debug("runtime file written", "path", s.RuntimeFilePath)
	return nil
}

// cleanupRuntimeFile removes the runtime file associated with the dev server.
func (s *reflectionServer) cleanupRuntimeFile() error {
	if s.RuntimeFilePath == "" {
		return nil
	}

	content, err := os.ReadFile(s.RuntimeFilePath)
	if err != nil {
		return fmt.Errorf("failed to read runtime file: %w", err)
	}

	var data runtimeFileData
	if err := json.Unmarshal(content, &data); err != nil {
		return fmt.Errorf("failed to unmarshal runtime data: %w", err)
	}

	if data.PID == os.Getpid() {
		if err := os.Remove(s.RuntimeFilePath); err != nil {
			return fmt.Errorf("failed to remove runtime file: %w", err)
		}
		slog.Debug("runtime file cleaned up", "path", s.RuntimeFilePath)
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
			slog.Warn("could not find project root (go.mod not found)")
			return os.Getwd()
		}
		dir = parent
	}
}

// serveMux returns a new ServeMux configured for the required Reflection API endpoints.
func serveMux(r *registry.Registry) *http.ServeMux {
	mux := http.NewServeMux()
	// Skip wrapHandler here to avoid logging constant polling requests.
	mux.HandleFunc("GET /api/__health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	mux.HandleFunc("GET /api/actions", wrapHandler(handleListActions(r)))
	mux.HandleFunc("POST /api/runAction", wrapHandler(handleRunAction(r)))
	mux.HandleFunc("POST /api/notify", wrapHandler(handleNotify(r)))
	return mux
}

// handleRunAction looks up an action by name in the registry, runs it with the
// provided JSON input, and writes back the JSON-marshaled request.
func handleRunAction(reg *registry.Registry) func(w http.ResponseWriter, r *http.Request) error {
	return func(w http.ResponseWriter, r *http.Request) error {
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

		logger.FromContext(ctx).Debug("running action", "key", body.Key, "stream", stream)

		var cb streamingCallback[json.RawMessage]
		if stream {
			w.Header().Set("Content-Type", "text/plain")
			w.Header().Set("Transfer-Encoding", "chunked")
			// Stream results are newline-separated JSON.
			cb = func(ctx context.Context, msg json.RawMessage) error {
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

		var contextMap core.ActionContext = nil
		if body.Context != nil {
			json.Unmarshal(body.Context, &contextMap)
		}

		resp, err := runAction(ctx, reg, body.Key, body.Input, cb, contextMap)
		if err != nil {
			return err
		}

		return writeJSON(ctx, w, resp)
	}
}

// handleNotify configures the telemetry server URL from the request.
func handleNotify(reg *registry.Registry) func(w http.ResponseWriter, r *http.Request) error {
	return func(w http.ResponseWriter, r *http.Request) error {
		var body struct {
			TelemetryServerURL       string `json:"telemetryServerUrl"`
			ReflectionApiSpecVersion int    `json:"reflectionApiSpecVersion"`
		}

		defer r.Body.Close()
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			return &base.HTTPError{Code: http.StatusBadRequest, Err: err}
		}

		if os.Getenv("GENKIT_TELEMETRY_SERVER") == "" && body.TelemetryServerURL != "" {
			reg.TracingState().WriteTelemetryImmediate(tracing.NewHTTPTelemetryClient(body.TelemetryServerURL))
			slog.Debug("connected to telemetry server", "url", body.TelemetryServerURL)
		}

		if body.ReflectionApiSpecVersion != internal.GENKIT_REFLECTION_API_SPEC_VERSION {
			slog.Error("Genkit CLI version is not compatible with runtime library. Please use `genkit-cli` version compatible with runtime library version.")
		}

		w.WriteHeader(http.StatusOK)
		_, err := w.Write([]byte("OK"))
		return err
	}
}

// handleListActions lists all the registered actions.
func handleListActions(reg *registry.Registry) func(w http.ResponseWriter, r *http.Request) error {
	return func(w http.ResponseWriter, r *http.Request) error {
		descs := reg.ListActions()
		descMap := map[string]action.Desc{}
		for _, d := range descs {
			descMap[d.Key] = d
		}
		return writeJSON(r.Context(), w, descMap)
	}
}

// TODO: Pull these from common types in genkit-tools.

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

// writeJSON writes a JSON-marshaled value to the response writer.
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

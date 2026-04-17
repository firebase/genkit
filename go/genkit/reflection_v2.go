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
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal"
)

// JSON-RPC 2.0 error codes.
const (
	jsonRPCMethodNotFound = -32601
	jsonRPCInvalidParams  = -32602
	jsonRPCServerError    = -32000
)

// jsonRPCRequest represents an incoming JSON-RPC 2.0 request from the manager.
type jsonRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
	ID      string          `json:"id,omitempty"`
}

// jsonRPCResponse is an outgoing JSON-RPC 2.0 response.
type jsonRPCResponse struct {
	JSONRPC string        `json:"jsonrpc"`
	Result  any           `json:"result,omitempty"`
	Error   *jsonRPCError `json:"error,omitempty"`
	ID      string        `json:"id"`
}

// jsonRPCNotification is an outgoing JSON-RPC 2.0 notification (no ID).
type jsonRPCNotification struct {
	JSONRPC string `json:"jsonrpc"`
	Method  string `json:"method"`
	Params  any    `json:"params,omitempty"`
}

// jsonRPCError is the error object in a JSON-RPC 2.0 error response.
type jsonRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// reflectionRunActionResponse is the success payload for a runAction request.
// Not in the generated schema because only the runtime produces it.
type reflectionRunActionResponse struct {
	Result    json.RawMessage `json:"result"`
	Telemetry telemetry       `json:"telemetry"`
}

// reflectionServerV2 is a WebSocket client that connects to the CLI's
// reflection manager and handles JSON-RPC 2.0 requests.
type reflectionServerV2 struct {
	g             *Genkit
	activeActions *activeActionsMap

	ctx     context.Context
	writeMu sync.Mutex // Serializes writes to conn.
	conn    *websocket.Conn
}

// reflectionServerV2Options configures the V2 reflection client.
type reflectionServerV2Options struct {
	Name string // App name (optional, defaults to the runtime ID).
	URL  string // WebSocket URL of the CLI manager.
}

// startReflectionServerV2 connects to the CLI's WebSocket server, registers
// this runtime, and spawns a goroutine to handle incoming reflection requests.
// Returns once registration has been sent (or an error has been reported).
func startReflectionServerV2(ctx context.Context, g *Genkit, opts reflectionServerV2Options, errCh chan<- error, serverStartCh chan<- struct{}) *reflectionServerV2 {
	if g == nil {
		errCh <- fmt.Errorf("nil Genkit provided")
		return nil
	}

	conn, _, err := websocket.Dial(ctx, opts.URL, nil)
	if err != nil {
		errCh <- fmt.Errorf("failed to connect to reflection V2 server at %s: %w", opts.URL, err)
		return nil
	}

	s := &reflectionServerV2{
		g:             g,
		activeActions: newActiveActionsMap(),
		ctx:           ctx,
		conn:          conn,
	}

	slog.Debug("reflection V2: connected", "url", opts.URL)

	if err := s.register(opts.Name); err != nil {
		conn.Close(websocket.StatusInternalError, "registration failed")
		errCh <- fmt.Errorf("failed to register with reflection V2 server: %w", err)
		return nil
	}

	close(serverStartCh)

	go func() {
		defer conn.Close(websocket.StatusNormalClosure, "shutting down")
		s.readLoop(ctx)
	}()

	return s
}

// register sends a registration notification to the manager.
func (s *reflectionServerV2) register(name string) error {
	runtimeID := os.Getenv("GENKIT_RUNTIME_ID")
	if runtimeID == "" {
		runtimeID = strconv.Itoa(os.Getpid())
	}
	if name == "" {
		name = runtimeID
	}

	return s.sendNotification("register", &ReflectionRegisterParams{
		ID:                       runtimeID,
		PID:                      os.Getpid(),
		Name:                     name,
		GenkitVersion:            "go/" + internal.Version,
		ReflectionApiSpecVersion: internal.GENKIT_REFLECTION_API_SPEC_VERSION,
	})
}

// readLoop reads and dispatches JSON-RPC messages until the context is
// cancelled or the connection is closed.
func (s *reflectionServerV2) readLoop(ctx context.Context) {
	for {
		var req jsonRPCRequest
		if err := wsjson.Read(ctx, s.conn, &req); err != nil {
			if ctx.Err() == nil && websocket.CloseStatus(err) == -1 {
				slog.Error("reflection V2: failed to read message", "err", err)
			}
			return
		}

		if req.JSONRPC != "2.0" || req.Method == "" {
			continue
		}

		go s.handleRequest(ctx, &req)
	}
}

// handleRequest dispatches a JSON-RPC request to the appropriate handler.
// Each handler is responsible for sending its own response (or none, for
// notifications). Unknown methods with a request ID return "method not found";
// unknown notifications are logged and ignored.
func (s *reflectionServerV2) handleRequest(ctx context.Context, req *jsonRPCRequest) {
	switch req.Method {
	case "listActions":
		s.handleListActions(ctx, req)
	case "listValues":
		s.handleListValues(req)
	case "runAction":
		s.handleRunAction(ctx, req)
	case "cancelAction":
		s.handleCancelAction(req)
	case "configure":
		s.handleConfigure(req)
	case "sendInputStreamChunk", "endInputStream":
		// Bidirectional input streaming is not yet implemented.
		slog.Debug("reflection V2: method not implemented", "method", req.Method)
	default:
		if req.ID != "" {
			s.sendErrorResponse(req.ID, jsonRPCMethodNotFound, "method not found: "+req.Method, nil)
		} else {
			slog.Debug("reflection V2: unknown notification", "method", req.Method)
		}
	}
}

// handleListActions responds with all registered and resolvable actions.
func (s *reflectionServerV2) handleListActions(ctx context.Context, req *jsonRPCRequest) {
	if req.ID == "" {
		return
	}
	ads := listResolvableActions(ctx, s.g)
	actionsMap := make(map[string]any, len(ads))
	for _, d := range ads {
		actionsMap[d.Key] = d
	}
	s.sendResponse(req.ID, struct {
		Actions map[string]any `json:"actions"`
	}{Actions: actionsMap})
}

// handleListValues responds with registered values. The "type" param is
// parsed for protocol compliance but the Go registry does not currently
// support filtering by type, so all values are returned.
func (s *reflectionServerV2) handleListValues(req *jsonRPCRequest) {
	if req.ID == "" {
		return
	}

	var params ReflectionListValuesParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		s.sendErrorResponse(req.ID, jsonRPCInvalidParams, "invalid params: "+err.Error(), nil)
		return
	}

	s.sendResponse(req.ID, ReflectionListValuesResponse(s.g.reg.ListValues()))
}

// handleRunAction executes an action and sends the result (with optional streaming).
func (s *reflectionServerV2) handleRunAction(ctx context.Context, req *jsonRPCRequest) {
	if req.ID == "" {
		return
	}

	var params ReflectionRunActionParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		s.sendErrorResponse(req.ID, jsonRPCInvalidParams, "invalid params: "+err.Error(), nil)
		return
	}

	slog.Debug("reflection V2: running action", "key", params.Key, "stream", params.Stream)

	actionCtx, cancel := context.WithCancel(ctx)
	defer cancel()

	// Capture the trace ID asynchronously so we can both track the action for
	// cancellation and include the trace ID in any error we send back.
	var traceIDMu sync.Mutex
	var traceID string

	telemetryCb := func(tid, _ string) {
		traceIDMu.Lock()
		traceID = tid
		traceIDMu.Unlock()

		s.activeActions.Set(tid, &activeAction{
			cancel:    cancel,
			startTime: time.Now(),
			traceID:   tid,
		})

		s.sendNotification("runActionState", &ReflectionRunActionStateParams{
			RequestID: req.ID,
			State:     &ReflectionRunActionStateParamsState{TraceID: tid},
		})
	}

	var streamCb streamingCallback[json.RawMessage]
	if params.Stream {
		streamCb = func(_ context.Context, chunk json.RawMessage) error {
			return s.sendNotification("streamChunk", &ReflectionStreamChunkParams{
				RequestID: req.ID,
				Chunk:     chunk,
			})
		}
	}

	contextMap := core.ActionContext{}
	if params.Context != nil {
		if err := json.Unmarshal(params.Context, &contextMap); err != nil {
			s.sendErrorResponse(req.ID, jsonRPCInvalidParams, "invalid context: "+err.Error(), nil)
			return
		}
	}

	actionCtx = tracing.WithTelemetryCallback(actionCtx, telemetryCb)
	resp, err := runAction(actionCtx, s.g, params.Key, params.Input, params.TelemetryLabels, streamCb, contextMap)

	traceIDMu.Lock()
	capturedTraceID := traceID
	traceIDMu.Unlock()
	if capturedTraceID != "" {
		s.activeActions.Delete(capturedTraceID)
	}

	if err != nil {
		s.sendRunActionError(req.ID, err, capturedTraceID)
		return
	}

	s.sendResponse(req.ID, &reflectionRunActionResponse{
		Result:    resp.Result,
		Telemetry: telemetry{TraceID: resp.Telemetry.TraceID},
	})
}

// sendRunActionError maps a runAction error to a JSON-RPC error response
// with a Status-shaped data field matching the JS implementation.
func (s *reflectionServerV2) sendRunActionError(id string, err error, traceID string) {
	code := core.INTERNAL
	msg := err.Error()
	if errors.Is(err, context.Canceled) {
		code = core.CANCELLED
		msg = "Action was cancelled"
	}

	details := map[string]any{}
	if traceID != "" {
		details["traceId"] = traceID
	}
	var ge *core.GenkitError
	if errors.As(err, &ge) && ge.Details != nil {
		if stack, ok := ge.Details["stack"].(string); ok {
			details["stack"] = stack
		}
	}

	data := map[string]any{
		"code":    core.StatusNameToCode[code],
		"message": msg,
	}
	if len(details) > 0 {
		data["details"] = details
	}

	s.sendErrorResponse(id, jsonRPCServerError, msg, data)
}

// handleConfigure processes a configuration notification from the manager.
func (s *reflectionServerV2) handleConfigure(req *jsonRPCRequest) {
	var params ReflectionConfigureParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		slog.Error("reflection V2: invalid configure params", "err", err)
		return
	}
	configureTelemetry(params.TelemetryServerURL)
}

// handleCancelAction cancels an in-flight action by trace ID.
func (s *reflectionServerV2) handleCancelAction(req *jsonRPCRequest) {
	if req.ID == "" {
		return
	}

	var params ReflectionCancelActionParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		s.sendErrorResponse(req.ID, jsonRPCInvalidParams, "invalid params: "+err.Error(), nil)
		return
	}
	if params.TraceID == "" {
		s.sendErrorResponse(req.ID, jsonRPCInvalidParams, "traceId is required", nil)
		return
	}

	action, ok := s.activeActions.Get(params.TraceID)
	if !ok {
		s.sendErrorResponse(req.ID, jsonRPCServerError, "Action not found or already completed", nil)
		return
	}

	action.cancel()
	s.activeActions.Delete(params.TraceID)
	s.sendResponse(req.ID, &ReflectionCancelActionResponse{Message: "Action cancelled"})
}

// sendResponse sends a JSON-RPC success response. Send errors are logged but
// not returned: the read loop will pick up on a broken connection on its
// next read.
func (s *reflectionServerV2) sendResponse(id string, result any) {
	if err := s.send(&jsonRPCResponse{JSONRPC: "2.0", Result: result, ID: id}); err != nil {
		slog.Error("reflection V2: failed to send response", "err", err, "id", id)
	}
}

// sendErrorResponse sends a JSON-RPC error response.
func (s *reflectionServerV2) sendErrorResponse(id string, code int, message string, data any) {
	if err := s.send(&jsonRPCResponse{
		JSONRPC: "2.0",
		Error:   &jsonRPCError{Code: code, Message: message, Data: data},
		ID:      id,
	}); err != nil {
		slog.Error("reflection V2: failed to send error response", "err", err, "id", id)
	}
}

// sendNotification sends a JSON-RPC notification (no ID, no response expected).
func (s *reflectionServerV2) sendNotification(method string, params any) error {
	return s.send(&jsonRPCNotification{JSONRPC: "2.0", Method: method, Params: params})
}

// send writes a JSON message to the WebSocket connection.
// It is safe for concurrent use.
func (s *reflectionServerV2) send(msg any) error {
	s.writeMu.Lock()
	defer s.writeMu.Unlock()
	return wsjson.Write(s.ctx, s.conn, msg)
}

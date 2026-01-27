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
	"fmt"
	"log/slog"
	"os"
	"runtime/debug"
	"sync"
	"time"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal"
	"github.com/gorilla/websocket"
)

// jsonRpcRequest represents a JSON-RPC 2.0 request or notification.
type jsonRpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
	ID      interface{}     `json:"id,omitempty"` // number or string
}

// jsonRpcResponse represents a JSON-RPC 2.0 response.
type jsonRpcResponse struct {
	JSONRPC string        `json:"jsonrpc"`
	Result  interface{}   `json:"result,omitempty"`
	Error   *jsonRpcError `json:"error,omitempty"`
	ID      interface{}   `json:"id"`
}

// jsonRpcError represents a JSON-RPC 2.0 error.
type jsonRpcError struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

// reflectionClientV2 handles the V2 Reflection API over WebSocket.
type reflectionClientV2 struct {
	g             *Genkit
	url           string
	ws            *websocket.Conn
	activeActions *activeActionsMap
	mu            sync.Mutex
}

// startReflectionClientV2 starts the Reflection API V2 client.
// It connects to the runtime manager via WebSocket.
func startReflectionClientV2(ctx context.Context, g *Genkit, url string, errCh chan<- error) *reflectionClientV2 {
	if g == nil {
		errCh <- fmt.Errorf("nil Genkit provided")
		return nil
	}

	client := &reflectionClientV2{
		g:             g,
		url:           url,
		activeActions: newActiveActionsMap(),
	}

	go client.run(ctx, errCh)

	return client
}

func (c *reflectionClientV2) run(ctx context.Context, errCh chan<- error) {
	slog.Info("Connecting to Reflection V2 server", "url", c.url)

	for {
		select {
		case <-ctx.Done():
			return
		default:
		}

		conn, _, err := websocket.DefaultDialer.Dial(c.url, nil)
		if err != nil {
			slog.Debug("Failed to connect to Reflection V2 server, retrying in 1s...", "error", err)
			time.Sleep(1 * time.Second)
			continue
		}

		c.mu.Lock()
		c.ws = conn
		c.mu.Unlock()

		slog.Info("Connected to Reflection V2 server")

		// Register immediately upon connection
		if err := c.register(); err != nil {
			slog.Error("Failed to register", "error", err)
			conn.Close()
			time.Sleep(1 * time.Second)
			continue
		}

		// Handle messages
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				slog.Error("WebSocket read error", "error", err)
				break
			}

			go c.handleMessage(ctx, message)
		}

		c.mu.Lock()
		c.ws = nil
		c.mu.Unlock()
		conn.Close()
		slog.Info("Disconnected from Reflection V2 server")
	}
}

func (c *reflectionClientV2) register() error {
	req := jsonRpcRequest{
		JSONRPC: "2.0",
		Method:  "register",
		Params: mustMarshal(map[string]interface{}{
			"id":                       c.runtimeID(),
			"name":                     c.runtimeID(),
			"pid":                      os.Getpid(),
			"genkitVersion":            "go/" + internal.Version,
			"reflectionApiSpecVersion": internal.GENKIT_REFLECTION_API_SPEC_VERSION,
			"envs":                     []string{"dev"}, // TODO: Make configurable
		}),
	}
	return c.send(req)
}

func (c *reflectionClientV2) runtimeID() string {
	// Simple runtime ID generation
	return fmt.Sprintf("%d", os.Getpid())
}

func (c *reflectionClientV2) handleMessage(ctx context.Context, data []byte) {
	slog.Debug("Received V2 Message", "data", string(data))
	var req jsonRpcRequest
	if err := json.Unmarshal(data, &req); err != nil {
		slog.Error("Failed to unmarshal JSON-RPC message", "error", err)
		return
	}

	if req.Method != "" {
		if req.ID != nil {
			// Request
			c.handleRequest(ctx, &req)
		} else {
			// Notification
			c.handleNotification(ctx, &req)
		}
	} else if req.ID != nil {
		// Response to our request
		// For now, just log debug. We don't currently send requests that expect responses (except register, which we ignore).
		slog.Debug("Received response", "id", req.ID)
	}
}

func (c *reflectionClientV2) send(msg interface{}) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.ws == nil {
		return fmt.Errorf("websocket not connected")
	}

	bytes, _ := json.Marshal(msg)
	slog.Debug("Sending V2 Message", "data", string(bytes))

	// Write JSON directly assumes msg is marshallable
	return c.ws.WriteJSON(msg)
}

func (c *reflectionClientV2) handleRequest(ctx context.Context, req *jsonRpcRequest) {
	var result interface{}
	var err *jsonRpcError
	handled := false

	defer func() {
		if handled {
			return
		}
		if r := recover(); r != nil {
			stack := string(debug.Stack())
			slog.Error("Panic in handleRequest", "panic", r, "stack", stack)
			err = &jsonRpcError{
				Code:    -32000,
				Message: fmt.Sprintf("Internal error: %v", r),
				Data: map[string]string{
					"stack": stack,
				},
			}
		}

		resp := jsonRpcResponse{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  result,
			Error:   err,
		}
		if sendErr := c.send(resp); sendErr != nil {
			slog.Error("Failed to send JSON-RPC response", "error", sendErr)
		}
	}()

	switch req.Method {
	case "listActions":
		result = c.handleListActions(ctx)
	case "listValues":
		result, err = c.handleListValues(ctx, req.Params)
	case "runAction":
		// runAction handles sending its own response/notifications
		c.handleRunAction(ctx, req)
		handled = true
	case "cancelAction":
		result, err = c.handleCancelAction(ctx, req.Params)
	default:
		err = &jsonRpcError{
			Code:    -32601,
			Message: fmt.Sprintf("Method not found: %s", req.Method),
		}
	}
}

func (c *reflectionClientV2) handleNotification(ctx context.Context, req *jsonRpcRequest) {
	switch req.Method {
	case "configure":
		c.handleConfigure(req.Params)
	default:
		slog.Debug("Unknown notification", "method", req.Method)
	}
}

func (c *reflectionClientV2) handleListActions(ctx context.Context) interface{} {
	ads := listResolvableActions(ctx, c.g)
	descMap := map[string]api.ActionDesc{}
	for _, d := range ads {
		descMap[d.Key] = d
	}
	return descMap
}

func (c *reflectionClientV2) handleListValues(ctx context.Context, params json.RawMessage) (interface{}, *jsonRpcError) {
	var p struct {
		Type string `json:"type"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, &jsonRpcError{Code: -32602, Message: "Invalid params"}
	}

	if p.Type == "defaultModel" {
		defaultModel := c.g.reg.LookupValue(api.DefaultModelKey)
		return map[string]interface{}{
			api.DefaultModelKey: defaultModel,
		}, nil
	}

	// Support for other values can be added here

	// Return empty map if not found/supported, or we could return all values if type is empty?
	// For now, consistent with JS, we might want to just list what resides in registry for that type.
	// But Genkit Go registry uses string keys for values, not strictly typed buckets.
	// If the user asks for random type, we return empty.

	vals := c.g.reg.ListValues()
	// Filter if needed, but registry just gives all currently.
	// Since JS impl specific code for "model", "prompt" etc in listValues is distinct from registry.listValues,
	// checking strictly for defaultModel is what was requested in the plan.

	return vals, nil
}

func (c *reflectionClientV2) handleRunAction(ctx context.Context, req *jsonRpcRequest) {
	var params struct {
		Key             string          `json:"key"`
		Input           json.RawMessage `json:"input"`
		Context         json.RawMessage `json:"context"`
		TelemetryLabels json.RawMessage `json:"telemetryLabels"`
		Stream          bool            `json:"stream"`
	}
	if err := json.Unmarshal(req.Params, &params); err != nil {
		c.sendError(req.ID, -32602, "Invalid params", nil)
		return
	}

	// Create cancellable context
	actionCtx, cancel := context.WithCancel(ctx)

	// Streaming callback
	var cb streamingCallback[json.RawMessage]
	if params.Stream {
		cb = func(ctx context.Context, msg json.RawMessage) error {
			// Notify streamChunk
			notif := jsonRpcRequest{
				JSONRPC: "2.0",
				Method:  "streamChunk",
				Params: mustMarshal(map[string]interface{}{
					"requestId": req.ID,
					"chunk":     msg,
				}),
			}
			return c.send(notif)
		}
	}

	// Telemetry callback
	var mu sync.Mutex
	sentTraceIDs := make(map[string]bool)

	telemetryCb := func(tid string, sid string) {
		mu.Lock()
		if sentTraceIDs[tid] {
			mu.Unlock()
			return
		}
		sentTraceIDs[tid] = true
		mu.Unlock()

		// Notify runActionState
		c.activeActions.Set(tid, &activeAction{
			cancel:    cancel,
			startTime: time.Now(),
			traceID:   tid,
		})

		notif := jsonRpcRequest{
			JSONRPC: "2.0",
			Method:  "runActionState",
			Params: mustMarshal(map[string]interface{}{
				"requestId": req.ID,
				"state": map[string]string{
					"traceId": tid,
				},
			}),
		}
		c.send(notif)
	}

	actionCtx = tracing.WithTelemetryCallback(actionCtx, telemetryCb)

	var contextMap core.ActionContext = nil
	if params.Context != nil {
		json.Unmarshal(params.Context, &contextMap)
	}

	// Run action
	// We run this synchronously in the handleMessage goroutine.
	// Panic recovery is handled by handleRequest's defer.

	resp, err := runAction(actionCtx, c.g, params.Key, params.Input, params.TelemetryLabels, cb, contextMap)

	if resp != nil && resp.Telemetry.TraceID != "" {
		c.activeActions.Delete(resp.Telemetry.TraceID)
	}

	if err != nil {
		// Handle error
		details := &core.ReflectionErrorDetails{}
		if resp != nil && resp.Telemetry.TraceID != "" {
			details.TraceID = &resp.Telemetry.TraceID
		}

		// Massage error similar to V1
		refErr := core.ToReflectionError(err)
		refErr.Details.TraceID = details.TraceID

		c.sendError(req.ID, -32000, refErr.Message, refErr)
		return
	}

	// Success
	c.sendResponse(req.ID, map[string]interface{}{
		"result": resp.Result,
		"telemetry": map[string]string{
			"traceId": resp.Telemetry.TraceID,
		},
	})
}

func (c *reflectionClientV2) handleCancelAction(ctx context.Context, params json.RawMessage) (interface{}, *jsonRpcError) {
	var p struct {
		TraceID string `json:"traceId"`
	}
	if err := json.Unmarshal(params, &p); err != nil {
		return nil, &jsonRpcError{Code: -32602, Message: "Invalid params"}
	}

	if p.TraceID == "" {
		return nil, &jsonRpcError{Code: -32602, Message: "traceId is required"}
	}

	action, exists := c.activeActions.Get(p.TraceID)
	if !exists {
		return nil, &jsonRpcError{Code: 404, Message: "Action not found or already completed"}
	}

	action.cancel()
	c.activeActions.Delete(p.TraceID)

	return map[string]string{"message": "Action cancelled"}, nil
}

func (c *reflectionClientV2) handleConfigure(params json.RawMessage) {
	var p struct {
		TelemetryServerURL string `json:"telemetryServerUrl"`
	}
	if err := json.Unmarshal(params, &p); err == nil {
		if os.Getenv("GENKIT_TELEMETRY_SERVER") == "" && p.TelemetryServerURL != "" {
			tracing.WriteTelemetryImmediate(tracing.NewHTTPTelemetryClient(p.TelemetryServerURL))
			slog.Debug("connected to telemetry server", "url", p.TelemetryServerURL)
		}
	}
}

func (c *reflectionClientV2) sendError(id interface{}, code int, message string, data interface{}) error {
	return c.send(jsonRpcResponse{
		JSONRPC: "2.0",
		ID:      id,
		Error: &jsonRpcError{
			Code:    code,
			Message: message,
			Data:    data,
		},
	})
}

func (c *reflectionClientV2) sendResponse(id interface{}, result interface{}) error {
	return c.send(jsonRpcResponse{
		JSONRPC: "2.0",
		ID:      id,
		Result:  result,
	})
}

func mustMarshal(v interface{}) []byte {
	b, err := json.Marshal(v)
	if err != nil {
		panic(err)
	}
	return b
}

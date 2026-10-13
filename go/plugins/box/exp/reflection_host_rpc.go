// Copyright 2026 Google LLC
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

package exp

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"time"

	"github.com/coder/websocket"

	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/status"
)

// register handles a runtime's register request. It returns the runtime, or
// nil when it was refused and the caller should drop the socket.
func (h *reflectionHost) register(conn *websocket.Conn, msg *rpcMessage) *connectedRuntime {
	var p struct {
		runtimeInfo
		Secret string `json:"secret"`
	}
	if err := json.Unmarshal(msg.Params, &p); err != nil || p.ID == "" {
		logger.Warn(context.Background(), "box: runtime register without an id; ignoring")
		return nil
	}
	rt := &connectedRuntime{info: p.runtimeInfo, conn: conn}
	if h.secret != "" && (p.Secret == "" || !secretsEqual(p.Secret, h.secret)) {
		err := rejectionError(p.runtimeInfo, p.Secret != "")
		logger.Warn(context.Background(), "box: runtime rejected", "error", err)
		if msg.ID != "" {
			// The auth code tells the runtime not to reconnect. Close only
			// after the write, or it may see a bare disconnect and retry.
			_ = rt.send(&rpcMessage{JSONRPC: "2.0", ID: msg.ID, Error: &rpcError{
				Code: reflectionAuthErrorCode, Message: "Invalid reflection secret.",
			}})
		}
		_ = conn.Close(websocket.StatusPolicyViolation, "unauthorized")
		h.notify(p.ID, err)
		return nil
	}
	h.mu.Lock()
	h.runtimes[p.ID] = rt
	h.mu.Unlock()
	if msg.ID != "" {
		_ = rt.send(&rpcMessage{JSONRPC: "2.0", ID: msg.ID, Result: json.RawMessage(`{}`)})
	}
	logger.Debug(context.Background(), "box: runtime registered", "id", p.ID, "pid", p.PID)
	h.notify(p.ID, nil)
	return rt
}

func rejectionError(info runtimeInfo, hadSecret bool) error {
	who := fmt.Sprintf("box runtime %s (pid %d", info.ID, info.PID)
	if info.GenkitVersion != "" {
		who += ", genkit " + info.GenkitVersion
	}
	who += ")"
	if hadSecret {
		return status.Errorf(status.ErrUnauthenticated, "%s was rejected: invalid reflection secret", who)
	}
	return status.Errorf(status.ErrUnauthenticated,
		"%s was rejected: it did not present a reflection secret; boxed runtimes need genkit >= %s", who, minSecretGenkitVersion)
}

// notify wakes everyone waiting for runtime id with err (nil: registered).
func (h *reflectionHost) notify(id string, err error) {
	h.mu.Lock()
	ws := h.waiters[id]
	delete(h.waiters, id)
	h.mu.Unlock()
	for _, w := range ws {
		w <- err
	}
}

// waitForRuntime blocks until runtime id registers, is rejected, or ctx ends.
func (h *reflectionHost) waitForRuntime(ctx context.Context, id string) error {
	h.mu.Lock()
	if _, ok := h.runtimes[id]; ok {
		h.mu.Unlock()
		return nil
	}
	ch := make(chan error, 1)
	h.waiters[id] = append(h.waiters[id], ch)
	h.mu.Unlock()
	select {
	case err := <-ch:
		return err
	case <-ctx.Done():
		h.mu.Lock()
		ws := h.waiters[id]
		for i, w := range ws {
			if w == ch {
				h.waiters[id] = append(ws[:i:i], ws[i+1:]...)
				break
			}
		}
		h.mu.Unlock()
		return ctx.Err()
	}
}

// errDisconnected is the internal code for a runtime that went away mid-call.
const errDisconnected = -1

// disconnect forgets rt and fails its pending calls: no response will come.
func (h *reflectionHost) disconnect(rt *connectedRuntime) {
	h.mu.Lock()
	if h.runtimes[rt.info.ID] == rt {
		delete(h.runtimes, rt.info.ID)
	}
	var orphaned []*pendingCall
	for id, c := range h.pending {
		if c.runtimeID == rt.info.ID {
			orphaned = append(orphaned, c)
			delete(h.pending, id)
		}
	}
	h.mu.Unlock()
	for _, c := range orphaned {
		c.done <- rpcMessage{Error: &rpcError{
			Code:    errDisconnected,
			Message: fmt.Sprintf("box runtime %s disconnected before responding", rt.info.ID),
		}}
	}
	logger.Debug(context.Background(), "box: runtime disconnected", "id", rt.info.ID)
}

// call sends method to runtime id and waits for its response. The pending
// entry is registered before the send, so chunks and trace ids that arrive
// before the response always find it.
func (h *reflectionHost) call(ctx context.Context, id, method string, params any, c *pendingCall) (json.RawMessage, error) {
	h.mu.Lock()
	rt := h.runtimes[id]
	if rt == nil {
		h.mu.Unlock()
		return nil, status.Errorf(status.ErrUnavailable, "box runtime %s is not connected", id)
	}
	reqID := strconv.FormatUint(h.seq.Add(1), 10)
	c.runtimeID = id
	c.done = make(chan rpcMessage, 1)
	h.pending[reqID] = c
	h.mu.Unlock()
	forget := func() {
		h.mu.Lock()
		delete(h.pending, reqID)
		h.mu.Unlock()
	}
	if err := rt.send(&struct {
		JSONRPC string `json:"jsonrpc"`
		Method  string `json:"method"`
		Params  any    `json:"params,omitempty"`
		ID      string `json:"id"`
	}{"2.0", method, params, reqID}); err != nil {
		forget()
		return nil, status.Errorf(status.ErrUnavailable, "box: send %s to runtime %s: %w", method, id, err)
	}
	select {
	case resp := <-c.done:
		if resp.Error == nil {
			return resp.Result, nil
		}
		if e, ok := decodeWireError(resp.Error.Data); ok {
			return nil, e
		}
		if resp.Error.Code == errDisconnected {
			return nil, status.Errorf(status.ErrUnavailable, "%s", resp.Error.Message)
		}
		if isActionNotFound(resp.Error.Code, resp.Error.Message) {
			return nil, status.Errorf(status.ErrNotFound, "box runtime %s: %s", id, resp.Error.Message)
		}
		return nil, status.Errorf(status.ErrUnknown, "box runtime %s: %s", id, resp.Error.Message)
	case <-ctx.Done():
		forget()
		return nil, ctx.Err()
	}
}

// runActionParams is the v2 runAction request. The embedded request's fields
// are omitempty, so unset ones are left out rather than sent as null: the JS
// runtime's schema accepts a missing optional field but rejects null.
type runActionParams struct {
	*RunActionRequest
	Stream      bool `json:"stream"`
	StreamInput bool `json:"streamInput"`
}

// rpcInvalidParams is JSON-RPC's "invalid params" error code.
const rpcInvalidParams = -32602

// actionNotFoundRE matches the message a JS runtime sends for a missing action.
var actionNotFoundRE = regexp.MustCompile(`^action \S+ not found$`)

// isActionNotFound reports whether a JSON-RPC error with no status data is a
// runtime's "no such action". The JS v2 runtime reports one as invalid params
// with only a message, so this matches on code plus message, as
// @genkit-ai/box does, until the runtime sends a status (a Go runtime already
// sends NOT_FOUND as error data, which is decoded before this is consulted).
func isActionNotFound(code int, msg string) bool {
	return code == rpcInvalidParams && actionNotFoundRE.MatchString(msg)
}

// runAction runs one action in runtime id. Cancelling ctx sends cancelAction
// with the trace id the runtime reported in runActionState.
func (h *reflectionHost) runAction(ctx context.Context, id string, r *RunActionRequest, opts *RunOptions) (*RunActionResult, error) {
	traceID := make(chan string, 1)
	c := &pendingCall{onTraceID: func(tid string) {
		select {
		case traceID <- tid:
		default:
		}
		if opts != nil && opts.OnTraceID != nil {
			opts.OnTraceID(tid)
		}
	}}
	stream := opts != nil && opts.OnChunk != nil
	if stream {
		c.onChunk = func(chunk json.RawMessage) {
			if err := opts.OnChunk(ctx, chunk); err != nil {
				logger.Debug(ctx, "box: stream callback failed", "error", err)
			}
		}
	}
	// On cancel, wait for the trace id (it may not have arrived yet) and
	// cancel the action in the runtime; stop once the call has returned.
	callDone := make(chan struct{})
	defer close(callDone)
	go func() {
		select {
		case <-ctx.Done():
		case <-callDone:
			return
		}
		select {
		case tid := <-traceID:
			h.cancelAction(id, tid)
		case <-callDone:
		}
	}()
	raw, err := h.call(ctx, id, "runAction", &runActionParams{RunActionRequest: r, Stream: stream}, c)
	if err != nil {
		return nil, err
	}
	var env runEnvelope
	if err := json.Unmarshal(raw, &env); err != nil {
		return nil, fmt.Errorf("box runAction %s: decode: %w", r.Key, err)
	}
	return &RunActionResult{Result: env.Result, TraceID: env.Telemetry.TraceID}, nil
}

// cancelAction cancels the action with traceID in runtime id, best effort.
func (h *reflectionHost) cancelAction(id, traceID string) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if _, err := h.call(ctx, id, "cancelAction", map[string]string{"traceId": traceID}, &pendingCall{}); err != nil {
		logger.Debug(ctx, "box: cancelAction failed", "runtime", id, "error", err)
	}
}

// listActions lists the actions runtime id serves.
func (h *reflectionHost) listActions(ctx context.Context, id string) (map[string]api.ActionDesc, error) {
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()
	raw, err := h.call(ctx, id, "listActions", nil, &pendingCall{})
	if err != nil {
		return nil, err
	}
	var res struct {
		Actions map[string]api.ActionDesc `json:"actions"`
	}
	if err := json.Unmarshal(raw, &res); err != nil {
		return nil, fmt.Errorf("box listActions: decode: %w", err)
	}
	return res.Actions, nil
}

// conn returns a [Conn] for runtime id.
func (h *reflectionHost) conn(id string) Conn { return &hostConn{h: h, id: id} }

type hostConn struct {
	h  *reflectionHost
	id string
}

func (c *hostConn) RunAction(ctx context.Context, r *RunActionRequest, opts *RunOptions) (*RunActionResult, error) {
	return c.h.runAction(ctx, c.id, r, opts)
}

func (c *hostConn) ListActions(ctx context.Context) (map[string]api.ActionDesc, error) {
	return c.h.listActions(ctx, c.id)
}

// close stops the server and drops every runtime.
func (h *reflectionHost) close() error {
	h.mu.Lock()
	rts := make([]*connectedRuntime, 0, len(h.runtimes))
	for _, rt := range h.runtimes {
		rts = append(rts, rt)
	}
	h.mu.Unlock()
	for _, rt := range rts {
		_ = rt.conn.Close(websocket.StatusGoingAway, "box closed")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := h.srv.Shutdown(ctx); err != nil && !errors.Is(err, context.DeadlineExceeded) {
		return err
	}
	return nil
}

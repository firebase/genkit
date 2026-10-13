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
	"net"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"

	"github.com/firebase/genkit/go/core/logger"
)

// maxMessageBytes caps one JSON-RPC message from a runtime. coder/websocket
// defaults to 32 KiB, too small for real tool outputs and agent snapshots.
const maxMessageBytes = 64 << 20

// minSecretGenkitVersion is the first Genkit version whose runtimes present a
// reflection secret; older ones connect without one and are rejected.
const minSecretGenkitVersion = "1.43"

// rpcMessage is any JSON-RPC 2.0 message on the wire: a request or
// notification (Method set) or a response (Result or Error set).
type rpcMessage struct {
	JSONRPC string          `json:"jsonrpc"`
	Method  string          `json:"method,omitempty"`
	Params  json.RawMessage `json:"params,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
	ID      string          `json:"id,omitempty"`
}

type rpcError struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data,omitempty"`
}

// runtimeInfo is what a runtime reports in register.
type runtimeInfo struct {
	ID            string `json:"id"`
	PID           int    `json:"pid,omitempty"`
	Name          string `json:"name,omitempty"`
	GenkitVersion string `json:"genkitVersion,omitempty"`
}

// connectedRuntime is a registered runtime and its socket.
type connectedRuntime struct {
	info    runtimeInfo
	conn    *websocket.Conn
	writeMu sync.Mutex
}

func (r *connectedRuntime) send(msg any) error {
	r.writeMu.Lock()
	defer r.writeMu.Unlock()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	return wsjson.Write(ctx, r.conn, msg)
}

// pendingCall is a request awaiting its response from one runtime.
type pendingCall struct {
	runtimeID string
	done      chan rpcMessage
	onChunk   func(json.RawMessage)
	onTraceID func(string)
}

// reflectionHost implements the reflection v2 manager role for box runtimes:
// a loopback WebSocket server runtimes dial (GENKIT_REFLECTION_V2_SERVER),
// with JSON-RPC requests flowing back over the same socket. It is standalone
// so the box has no dependency on developer tooling.
//
// Anything local could dial a loopback port, so runtimes must present the
// host's secret in register, the same handshake as the Genkit CLI.
type reflectionHost struct {
	secret string
	ln     net.Listener
	srv    *http.Server
	seq    atomic.Uint64

	mu       sync.Mutex
	runtimes map[string]*connectedRuntime
	pending  map[string]*pendingCall
	// waiters are notified when a runtime registers or is rejected.
	waiters map[string][]chan error
}

// newReflectionHost starts a host on a free loopback port. Runtimes must
// present secret; an empty secret accepts any runtime.
func newReflectionHost(secret string) (*reflectionHost, error) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return nil, fmt.Errorf("box: reflection host listen: %w", err)
	}
	h := &reflectionHost{
		secret:   secret,
		ln:       ln,
		runtimes: map[string]*connectedRuntime{},
		pending:  map[string]*pendingCall{},
		waiters:  map[string][]chan error{},
	}
	h.srv = &http.Server{Handler: http.HandlerFunc(h.accept), ReadHeaderTimeout: 10 * time.Second}
	go func() {
		if err := h.srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error(context.Background(), "box: reflection host stopped", "error", err)
		}
	}()
	return h, nil
}

// url is what runtimes dial.
func (h *reflectionHost) url() string { return "ws://" + h.ln.Addr().String() }

// port is the host's loopback port.
func (h *reflectionHost) port() int { return h.ln.Addr().(*net.TCPAddr).Port }

func (h *reflectionHost) accept(w http.ResponseWriter, r *http.Request) {
	conn, err := websocket.Accept(w, r, nil)
	if err != nil {
		return
	}
	conn.SetReadLimit(maxMessageBytes)
	h.serve(r.Context(), conn)
}

// serve reads one runtime's socket until it drops. Notifications are handled
// inline, which keeps stream chunks in wire order.
func (h *reflectionHost) serve(ctx context.Context, conn *websocket.Conn) {
	var rt *connectedRuntime
	defer func() {
		if rt != nil {
			h.disconnect(rt)
		}
		_ = conn.CloseNow()
	}()
	for {
		var msg rpcMessage
		if err := wsjson.Read(ctx, conn, &msg); err != nil {
			return
		}
		switch {
		case msg.Method == "register":
			if rt != nil {
				continue
			}
			if rt = h.register(conn, &msg); rt == nil {
				return
			}
		case rt == nil:
			// Nothing but register is accepted before register succeeds.
			return
		case msg.Method == "streamChunk":
			var p struct {
				RequestID string          `json:"requestId"`
				Chunk     json.RawMessage `json:"chunk"`
			}
			if json.Unmarshal(msg.Params, &p) == nil {
				if c := h.lookupPending(rt, p.RequestID); c != nil && c.onChunk != nil {
					c.onChunk(p.Chunk)
				}
			}
		case msg.Method == "runActionState":
			var p struct {
				RequestID string `json:"requestId"`
				State     struct {
					TraceID string `json:"traceId"`
				} `json:"state"`
			}
			if json.Unmarshal(msg.Params, &p) == nil && p.State.TraceID != "" {
				if c := h.lookupPending(rt, p.RequestID); c != nil && c.onTraceID != nil {
					c.onTraceID(p.State.TraceID)
				}
			}
		case msg.Method != "":
			logger.Debug(ctx, "box: reflection host ignoring method", "method", msg.Method)
		case msg.ID != "":
			h.resolve(rt, &msg)
		}
	}
}

// lookupPending returns the call reqID on rt's socket. Request ids are
// host-wide, so the runtime check keeps one runtime from answering for
// another.
func (h *reflectionHost) lookupPending(rt *connectedRuntime, reqID string) *pendingCall {
	h.mu.Lock()
	defer h.mu.Unlock()
	if c := h.pending[reqID]; c != nil && c.runtimeID == rt.info.ID {
		return c
	}
	return nil
}

// resolve delivers a response to its pending call.
func (h *reflectionHost) resolve(rt *connectedRuntime, msg *rpcMessage) {
	h.mu.Lock()
	c := h.pending[msg.ID]
	if c == nil || c.runtimeID != rt.info.ID {
		h.mu.Unlock()
		return
	}
	delete(h.pending, msg.ID)
	h.mu.Unlock()
	c.done <- *msg
}

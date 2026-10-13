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
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/status"
)

// reflectionClientV1 talks to a runtime's reflection v1 server over HTTP.
//
// V1 inverts v2's direction: the runtime is the server and the box is the
// client. That is what makes containers workable, since a published port
// forwards host to container, matching a dial-in client; the box needs no
// route back to the host. Only what [Conn] needs is implemented.
type reflectionClientV1 struct {
	baseURL string
	headers map[string]string
	http    *http.Client
}

// newReflectionClientV1 returns a client for the runtime at baseURL (e.g.
// http://127.0.0.1:3100). secret, when set, is sent on every request.
func newReflectionClientV1(baseURL, secret string, headers map[string]string) *reflectionClientV1 {
	h := map[string]string{}
	for k, v := range headers {
		h[k] = v
	}
	if secret != "" {
		h[reflectionSecretHeader] = secret
	}
	return &reflectionClientV1{
		baseURL: strings.TrimRight(baseURL, "/"),
		headers: h,
		// No overall timeout: streaming calls last as long as the action.
		http: &http.Client{},
	}
}

func (c *reflectionClientV1) newRequest(ctx context.Context, method, path string, body any) (*http.Request, error) {
	var r io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		r = bytes.NewReader(b)
	}
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, r)
	if err != nil {
		return nil, err
	}
	for k, v := range c.headers {
		req.Header.Set(k, v)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	return req, nil
}

// waitForReady polls /api/__health until the runtime answers, ctx ends, or
// timeout passes. Nothing dials a v1 client, so readiness has to be observed.
func (c *reflectionClientV1) waitForReady(ctx context.Context, timeout time.Duration) error {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	var lastErr error
	for {
		attempt, attemptCancel := context.WithTimeout(ctx, 2*time.Second)
		req, err := c.newRequest(attempt, http.MethodGet, "/api/__health", nil)
		if err != nil {
			attemptCancel()
			return err
		}
		resp, err := c.http.Do(req)
		if err == nil {
			_, _ = io.Copy(io.Discard, resp.Body)
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				attemptCancel()
				return nil
			}
			err = fmt.Errorf("health returned %d", resp.StatusCode)
		}
		attemptCancel()
		// Connection refused until the server binds; keep polling.
		lastErr = err
		select {
		case <-ctx.Done():
			if errors.Is(ctx.Err(), context.DeadlineExceeded) {
				return status.Errorf(status.ErrDeadlineExceeded,
					"timed out after %v waiting for box reflection server at %s (last error: %v)", timeout, c.baseURL, lastErr)
			}
			return ctx.Err()
		case <-time.After(150 * time.Millisecond):
		}
	}
}

// ListActions implements [Conn].
func (c *reflectionClientV1) ListActions(ctx context.Context) (map[string]api.ActionDesc, error) {
	req, err := c.newRequest(ctx, http.MethodGet, "/api/actions", nil)
	if err != nil {
		return nil, err
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("box listActions: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, httpError("listActions", resp)
	}
	var actions map[string]api.ActionDesc
	if err := json.NewDecoder(resp.Body).Decode(&actions); err != nil {
		return nil, fmt.Errorf("box listActions: decode: %w", err)
	}
	return actions, nil
}

// runEnvelope is the {result, error, telemetry} body v1 returns.
type runEnvelope struct {
	Result    json.RawMessage `json:"result"`
	Error     json.RawMessage `json:"error"`
	Telemetry struct {
		TraceID string `json:"traceId"`
	} `json:"telemetry"`
}

// RunAction implements [Conn]. Cancelling ctx cancels the action in the
// runtime too: v1 has no in-band cancel, so the client calls cancelAction with
// the trace id the response headers carry.
func (c *reflectionClientV1) RunAction(ctx context.Context, r *RunActionRequest, opts *RunOptions) (*RunActionResult, error) {
	stream := opts != nil && opts.OnChunk != nil
	path := "/api/runAction"
	if stream {
		path += "?stream=true"
	}
	req, err := c.newRequest(ctx, http.MethodPost, path, r)
	if err != nil {
		return nil, err
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("box runAction %s: %w", r.Key, err)
	}
	defer resp.Body.Close()

	traceID := resp.Header.Get("X-Genkit-Trace-Id")
	if traceID != "" {
		if opts != nil && opts.OnTraceID != nil {
			opts.OnTraceID(traceID)
		}
		// The request context ends the HTTP call, but the action keeps
		// running in the runtime until it is told to stop.
		stop := context.AfterFunc(ctx, func() { c.cancelAction(traceID) })
		defer stop()
	}
	if resp.StatusCode != http.StatusOK {
		return nil, httpError("runAction "+r.Key, resp)
	}

	var env runEnvelope
	if stream {
		err = readStream(ctx, resp.Body, opts.OnChunk, &env)
	} else {
		err = json.NewDecoder(resp.Body).Decode(&env)
	}
	if err != nil {
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		return nil, fmt.Errorf("box runAction %s: %w", r.Key, err)
	}
	if len(env.Error) > 0 && string(env.Error) != "null" {
		if e, ok := decodeWireError(env.Error); ok {
			return nil, e
		}
		return nil, status.Errorf(status.ErrUnknown, "box action %s failed: %s", r.Key, env.Error)
	}
	if env.Telemetry.TraceID != "" {
		traceID = env.Telemetry.TraceID
	}
	return &RunActionResult{Result: env.Result, TraceID: traceID}, nil
}

// readStream reads a streaming runAction body: newline-delimited JSON chunks
// whose final line is the {result}/{error} envelope rather than a chunk. A
// line is dispatched as a chunk only once the next one arrives, which tells a
// trailing envelope from a chunk without lookahead.
func readStream(ctx context.Context, body io.Reader, onChunk func(context.Context, json.RawMessage) error, env *runEnvelope) error {
	sc := bufio.NewScanner(body)
	sc.Buffer(make([]byte, 64*1024), 64*1024*1024)
	var pending []byte
	for sc.Scan() {
		line := bytes.TrimSpace(sc.Bytes())
		if len(line) == 0 {
			continue
		}
		if pending != nil {
			if err := onChunk(ctx, pending); err != nil {
				return err
			}
		}
		pending = bytes.Clone(line)
	}
	if err := sc.Err(); err != nil {
		return err
	}
	if pending == nil {
		return errors.New("stream ended without a result envelope")
	}
	return json.Unmarshal(pending, env)
}

// cancelAction asks the runtime to cancel the action with traceID. It is best
// effort and runs detached from the cancelled call's context.
func (c *reflectionClientV1) cancelAction(traceID string) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	req, err := c.newRequest(ctx, http.MethodPost, "/api/cancelAction", map[string]string{"traceId": traceID})
	if err != nil {
		return
	}
	resp, err := c.http.Do(req)
	if err != nil {
		logger.Debug(ctx, "box: cancelAction failed", "traceId", traceID, "error", err)
		return
	}
	_, _ = io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

// httpError turns a non-200 reflection response into an error, keeping the
// runtime's status when the body carries a reflection error.
func httpError(what string, resp *http.Response) error {
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	if resp.StatusCode == http.StatusUnauthorized {
		return status.Errorf(status.ErrUnauthenticated, "box %s: the runtime rejected the reflection secret", what)
	}
	if e, ok := decodeWireError(body); ok {
		return e
	}
	return status.Errorf(status.Base(status.FromHTTPCode(resp.StatusCode)), "box %s: HTTP %d: %s", what, resp.StatusCode, bytes.TrimSpace(body))
}

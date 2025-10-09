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
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/tracing"
)

func inc(_ context.Context, x int) (int, error) {
	return x + 1, nil
}

func dec(_ context.Context, x int) (int, error) {
	return x - 1, nil
}

func TestReflectionServer(t *testing.T) {
	t.Run("server startup and shutdown", func(t *testing.T) {
		g := Init(context.Background())

		tc := tracing.NewTestOnlyTelemetryClient()
		tracing.WriteTelemetryImmediate(tc)

		errCh := make(chan error, 1)
		serverStartCh := make(chan struct{})

		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		srv := startReflectionServer(ctx, g, errCh, serverStartCh)
		if srv == nil {
			t.Fatal("failed to start reflection server")
		}

		select {
		case err := <-errCh:
			t.Fatalf("server failed to start: %v", err)
		case <-serverStartCh:
			// Server started successfully
		case <-time.After(5 * time.Second):
			t.Fatal("timeout waiting for server to start")
		}

		if _, err := os.Stat(srv.RuntimeFilePath); err != nil {
			t.Errorf("runtime file not created: %v", err)
		}

		cancel()
		time.Sleep(100 * time.Millisecond)

		if _, err := os.Stat(srv.RuntimeFilePath); !os.IsNotExist(err) {
			t.Error("runtime file was not cleaned up")
		}
	})
}

func TestServeMux(t *testing.T) {
	g := Init(context.Background())

	tc := tracing.NewTestOnlyTelemetryClient()
	tracing.WriteTelemetryImmediate(tc)

	core.DefineAction(g.reg, "test/inc", api.ActionTypeCustom, nil, nil, inc)
	core.DefineAction(g.reg, "test/dec", api.ActionTypeCustom, nil, nil, dec)

	ts := httptest.NewServer(serveMux(g))
	defer ts.Close()

	t.Parallel()

	t.Run("health check", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/api/__health")
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if res.StatusCode != http.StatusOK {
			t.Errorf("health check failed: got status %d, want %d", res.StatusCode, http.StatusOK)
		}
	})

	t.Run("list actions", func(t *testing.T) {
		res, err := http.Get(ts.URL + "/api/actions")
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()

		var actions map[string]api.ActionDesc
		if err := json.NewDecoder(res.Body).Decode(&actions); err != nil {
			t.Fatal(err)
		}

		expectedKeys := []string{"/custom/test/inc", "/custom/test/dec"}
		for _, key := range expectedKeys {
			if _, ok := actions[key]; !ok {
				t.Errorf("action %q not found in response", key)
			}
		}
	})

	t.Run("run action", func(t *testing.T) {
		tests := []struct {
			name       string
			body       string
			wantStatus int
			wantResult string
		}{
			{
				name:       "valid increment",
				body:       `{"key": "/custom/test/inc", "input": 3}`,
				wantStatus: http.StatusOK,
				wantResult: "4",
			},
			{
				name:       "valid decrement",
				body:       `{"key": "/custom/test/dec", "input": 3}`,
				wantStatus: http.StatusOK,
				wantResult: "2",
			},
			{
				name:       "check telemetry labels",
				body:       `{"key": "/custom/test/dec", "input": 3,"telemetryLabels":{"test_k":"test_v"}}`,
				wantStatus: http.StatusOK,
				wantResult: "2",
			},
			{
				name:       "invalid action key",
				body:       `{"key": "/custom/test/invalid", "input": 3}`,
				wantStatus: http.StatusNotFound,
			},
			{
				name:       "invalid input type",
				body:       `{"key": "/custom/test/inc", "input": "not a number"}`,
				wantStatus: http.StatusBadRequest,
			},
		}

		for _, tt := range tests {
			t.Run(tt.name, func(t *testing.T) {
				res, err := http.Post(ts.URL+"/api/runAction", "application/json", strings.NewReader(tt.body))
				if err != nil {
					t.Fatal(err)
				}
				defer res.Body.Close()

				if res.StatusCode != tt.wantStatus {
					t.Errorf("got status %d, want %d", res.StatusCode, tt.wantStatus)
					return
				}

				if tt.wantResult != "" {
					var resp runActionResponse
					if err := json.NewDecoder(res.Body).Decode(&resp); err != nil {
						t.Fatal(err)
					}
					if g := string(resp.Result); g != tt.wantResult {
						t.Errorf("got result %q, want %q", g, tt.wantResult)
					}
					if resp.Telemetry.TraceID == "" {
						t.Error("expected non-empty trace ID")
					}
				}
			})
		}
	})

	t.Run("streaming action", func(t *testing.T) {
		streamingInc := func(_ context.Context, x int, cb streamingCallback[json.RawMessage]) (int, error) {
			for i := range x {
				msg, _ := json.Marshal(i)
				if err := cb(context.Background(), msg); err != nil {
					return 0, err
				}
			}
			return x, nil
		}
		core.DefineStreamingAction(g.reg, "test/streaming", api.ActionTypeCustom, nil, nil, streamingInc)

		body := `{"key": "/custom/test/streaming", "input": 3}`
		req, err := http.NewRequest("POST", ts.URL+"/api/runAction?stream=true", strings.NewReader(body))
		if err != nil {
			t.Fatal(err)
		}
		res, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()

		scanner := bufio.NewScanner(res.Body)

		for i := range 3 {
			if !scanner.Scan() {
				t.Fatalf("expected streaming chunk %d", i)
			}
			got := scanner.Text()
			want := fmt.Sprintf("%d", i)
			if got != want {
				t.Errorf("chunk %d: got %q, want %q", i, got, want)
			}
		}

		if !scanner.Scan() {
			t.Fatal("expected final response")
		}
		var resp runActionResponse
		if err := json.Unmarshal([]byte(scanner.Text()), &resp); err != nil {
			t.Fatal(err)
		}
		if g := string(resp.Result); g != "3" {
			t.Errorf("got final result %q, want %q", g, "3")
		}
		if resp.Telemetry.TraceID == "" {
			t.Error("expected non-empty trace ID")
		}

		if scanner.Scan() {
			t.Errorf("unexpected additional data: %q", scanner.Text())
		}
		if err := scanner.Err(); err != nil {
			t.Errorf("scanner error: %v", err)
		}
	})

	t.Run("notify endpoint", func(t *testing.T) {
		body := `{
			"telemetryServerURL": "http://localhost:9999",
			"reflectionApiSpecVersion": 1
		}`
		res, err := http.Post(ts.URL+"/api/notify", "application/json", strings.NewReader(body))
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()

		if res.StatusCode != http.StatusOK {
			t.Errorf("got status %d, want %d", res.StatusCode, http.StatusOK)
		}
	})
}

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
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/firebase/genkit/go/core/status"
)

func TestReflectionClientV1(t *testing.T) {
	ctx := context.Background()
	port := freePort(t)
	secret := newSecret()
	startFixture(t,
		reflectionEnabledEnv+"=true",
		fmt.Sprintf("GENKIT_REFLECTION_PORT=%d", port),
		reflectionSecretEnv+"="+secret,
	)
	url := fmt.Sprintf("http://127.0.0.1:%d", port)
	client := newReflectionClientV1(url, secret, nil)
	if err := client.waitForReady(ctx, 30*time.Second); err != nil {
		t.Fatal(err)
	}
	conformance(t, newSettlingConn(client, time.Second))

	t.Run("wrong secret", func(t *testing.T) {
		_, err := newReflectionClientV1(url, "nope", nil).ListActions(ctx)
		if status.Of(err) != status.Unauthenticated {
			t.Errorf("err = %v, want UNAUTHENTICATED", err)
		}
	})
}

func TestReflectionClientV1ReadyTimeout(t *testing.T) {
	client := newReflectionClientV1(fmt.Sprintf("http://127.0.0.1:%d", freePort(t)), "", nil)
	err := client.waitForReady(context.Background(), 300*time.Millisecond)
	if status.Of(err) != status.DeadlineExceeded {
		t.Errorf("err = %v, want DEADLINE_EXCEEDED", err)
	}
}

// startV2Fixture starts a fixture runtime that dials host as runtimeID with
// secret, and waits for it unless wait is false.
func startV2Fixture(t *testing.T, host *reflectionHost, runtimeID, secret string) {
	t.Helper()
	startFixture(t,
		reflectionEnabledEnv+"=true",
		reflectionV2ServerEnv+"="+host.url(),
		reflectionSecretEnv+"="+secret,
		runtimeIDEnv+"="+runtimeID,
	)
}

func newTestHost(t *testing.T) *reflectionHost {
	t.Helper()
	host, err := newReflectionHost(newSecret())
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = host.close() })
	return host
}

func TestReflectionHost(t *testing.T) {
	host := newTestHost(t)
	startV2Fixture(t, host, "rt-1", host.secret)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := host.waitForRuntime(ctx, "rt-1"); err != nil {
		t.Fatal(err)
	}
	conformance(t, newSettlingConn(host.conn("rt-1"), time.Second))
}

func TestReflectionHostRejectsWrongSecret(t *testing.T) {
	host := newTestHost(t)
	startV2Fixture(t, host, "rt-bad", "wrong")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	// The rejection is reported right away, not at the timeout.
	if err := host.waitForRuntime(ctx, "rt-bad"); status.Of(err) != status.Unauthenticated {
		t.Errorf("waitForRuntime = %v, want UNAUTHENTICATED", err)
	}
}

func TestReflectionHostFailsCallsOnDisconnect(t *testing.T) {
	host := newTestHost(t)
	startV2Fixture(t, host, "rt-2", host.secret)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := host.waitForRuntime(ctx, "rt-2"); err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() {
		_, err := newSettlingConn(host.conn("rt-2"), defaultSettleTimeout).RunAction(ctx, &RunActionRequest{Key: "/flow/block", Input: json.RawMessage(`"x"`)}, nil)
		done <- err
	}()
	time.Sleep(500 * time.Millisecond)
	// Drop the socket from the host side, as a crashed runtime would.
	host.mu.Lock()
	rt := host.runtimes["rt-2"]
	host.mu.Unlock()
	_ = rt.conn.CloseNow()
	select {
	case err := <-done:
		if status.Of(err) != status.Unavailable {
			t.Errorf("err = %v, want UNAVAILABLE", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("call to a dropped runtime did not fail")
	}
}

// TestRunActionParamsOmitUnset pins the wire shape a JS runtime accepts: its
// schema takes a missing optional field but rejects null.
func TestRunActionParamsOmitUnset(t *testing.T) {
	b, err := json.Marshal(&runActionParams{RunActionRequest: &RunActionRequest{Key: "/flow/f"}})
	if err != nil {
		t.Fatal(err)
	}
	if got, want := string(b), `{"key":"/flow/f","stream":false,"streamInput":false}`; got != want {
		t.Errorf("params = %s, want %s", got, want)
	}
	b, _ = json.Marshal(&runActionParams{RunActionRequest: &RunActionRequest{
		Key: "/agent/a", Input: json.RawMessage(`{}`), Init: json.RawMessage(`{}`),
		Context: map[string]any{"k": "v"}, TelemetryLabels: map[string]string{"l": "1"},
	}, Stream: true})
	for _, field := range []string{`"input":{}`, `"init":{}`, `"context":{"k":"v"}`, `"telemetryLabels":{"l":"1"}`, `"stream":true`} {
		if !strings.Contains(string(b), field) {
			t.Errorf("params %s are missing %s", b, field)
		}
	}
}

func TestIsActionNotFound(t *testing.T) {
	for _, tc := range []struct {
		code int
		msg  string
		want bool
	}{
		{rpcInvalidParams, "action /flow/nope not found", true},
		{rpcInvalidParams, "invalid input", false},
		{-32000, "action /flow/nope not found", false},
		{rpcInvalidParams, "snapshot for action /flow/x not found here", false},
	} {
		if got := isActionNotFound(tc.code, tc.msg); got != tc.want {
			t.Errorf("isActionNotFound(%d, %q) = %v, want %v", tc.code, tc.msg, got, tc.want)
		}
	}
}

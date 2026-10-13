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
	"fmt"
	"testing"
	"time"

	"github.com/firebase/genkit/go/core/status"
)

// startV1Fixture starts a fixture runtime serving reflection v1 on port with
// secret, the way an operator would start a sidecar.
func startV1Fixture(t *testing.T, port int, secret string) {
	t.Helper()
	startFixture(t,
		reflectionEnabledEnv+"=true",
		fmt.Sprintf("GENKIT_REFLECTION_PORT=%d", port),
		reflectionSecretEnv+"="+secret,
	)
}

func TestRemoteRunnerProxiesAFlow(t *testing.T) {
	ctx := context.Background()
	port, secret := freePort(t), newSecret()
	startV1Fixture(t, port, secret)
	b := New(newTestGenkit(), RemoteRunner(RemoteOptions{URL: fmt.Sprintf("http://127.0.0.1:%d/", port), Secret: secret}))
	t.Cleanup(func() { _ = b.Close(ctx) })

	out, err := NewStreamingFlow[int, string, countChunk](b, "count").Run(ctx, 2)
	if err != nil || out != "counted 2" {
		t.Fatalf("count = %q, %v; want counted 2", out, err)
	}
}

func TestRemoteRunnerMapsEveryKeyToOneRuntime(t *testing.T) {
	ctx := context.Background()
	port, secret := freePort(t), newSecret()
	startV1Fixture(t, port, secret)
	r := RemoteRunner(RemoteOptions{URL: fmt.Sprintf("http://127.0.0.1:%d", port), Secret: secret})
	b := New(newTestGenkit(), r, WithRoute(PerRequest))

	p1, _ := pidOf(t, ctx, b, "")
	p2, _ := pidOf(t, ctx, b, "")
	if p1 != p2 {
		t.Errorf("keys reached runtimes %d and %d, want one", p1, p2)
	}
	// Release (PerRequest released both keys) and Close leave it running.
	if err := b.Close(ctx); err != nil {
		t.Fatal(err)
	}
	if !processAlive(p1) {
		t.Error("Close stopped a runtime the runner does not own")
	}
	if _, err := r.Acquire(ctx, "another"); err != nil {
		t.Errorf("Acquire after Close = %v, want the runtime still reachable", err)
	}
}

func TestRemoteRunnerRetriesAFailedReadinessCheck(t *testing.T) {
	ctx := context.Background()
	port, secret := freePort(t), newSecret()
	r := RemoteRunner(RemoteOptions{URL: fmt.Sprintf("http://127.0.0.1:%d", port), Secret: secret, ReadyTimeout: 300 * time.Millisecond})
	if _, err := r.Acquire(ctx, "k"); status.Of(err) != status.DeadlineExceeded {
		t.Fatalf("Acquire before the runtime is up = %v, want DEADLINE_EXCEEDED", err)
	}
	startV1Fixture(t, port, secret)
	// The failure was not cached; once the runtime is up, Acquire succeeds.
	deadline := time.Now().Add(30 * time.Second)
	for {
		_, err := r.Acquire(ctx, "k")
		if err == nil {
			break
		}
		if time.Now().After(deadline) {
			t.Fatalf("Acquire never succeeded: %v", err)
		}
	}
}

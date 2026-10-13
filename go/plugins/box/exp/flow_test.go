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
	"slices"
	"testing"

	"go.opentelemetry.io/otel/sdk/trace/tracetest"

	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/genkit"
)

type countChunk struct {
	N int `json:"n"`
}

func TestStreamingFlowProxy(t *testing.T) {
	r := newFakeRunner(func(ctx context.Context, _ *RunActionRequest, opts *RunOptions) (any, error) {
		if opts == nil || opts.OnChunk == nil {
			t.Error("streaming call without OnChunk")
			return "", nil
		}
		for i := 1; i <= 3; i++ {
			if err := opts.OnChunk(ctx, json.RawMessage(mustJSON(t, countChunk{N: i}))); err != nil {
				return nil, err
			}
		}
		return "counted", nil
	})
	flow := NewStreamingFlow[int, string, countChunk](New(newTestGenkit(), r), "count")
	var got []int
	var out string
	for v, err := range flow.Stream(context.Background(), 3) {
		if err != nil {
			t.Fatal(err)
		}
		if v.Done {
			out = v.Output
		} else {
			got = append(got, v.Stream.N)
		}
	}
	if !slices.Equal(got, []int{1, 2, 3}) || out != "counted" {
		t.Errorf("chunks %v, output %q; want [1 2 3], counted", got, out)
	}
	if _, _, calls := r.snapshot(); calls[0].req.Key != "/flow/count" {
		t.Errorf("box key = %q, want /flow/count", calls[0].req.Key)
	}
}

func TestDefineFlowFromRenamesAndCallsOriginal(t *testing.T) {
	g := newTestGenkit()
	r := newFakeRunner(nil)
	real := genkit.NewFlow("echo", func(_ context.Context, in shoutIn) (shoutIn, error) { return in, nil })
	proxy := DefineFlowFrom(New(g, r), real, "boxedEcho")
	if genkit.LookupAction(g, api.KeyFromName(api.ActionTypeFlow, "boxedEcho")) == nil {
		t.Fatal("boxedEcho not registered")
	}
	if mustJSON(t, proxy.Desc().InputSchema) != mustJSON(t, real.Desc().InputSchema) {
		t.Errorf("input schema %v, want %v", proxy.Desc().InputSchema, real.Desc().InputSchema)
	}
	out, err := proxy.Run(context.Background(), shoutIn{Text: "hi"})
	if err != nil || out.Text != "hi" {
		t.Errorf("Run = %+v, %v; want the echoed input", out, err)
	}
	if _, _, calls := r.snapshot(); calls[0].req.Key != "/flow/echo" {
		t.Errorf("box key = %q, want the original /flow/echo", calls[0].req.Key)
	}
}

func TestFlowSchemaSpecRequiresAny(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Error("WithOutputSchema on a typed Out did not panic")
		}
	}()
	NewFlow[any, string](New(newTestGenkit(), newFakeRunner(nil)), "bad", WithOutputSchema(map[string]any{"type": "string"}))
}

func TestProxySpanIsMarkedAndLinked(t *testing.T) {
	recorder := tracetest.NewSpanRecorder()
	tp := tracing.TracerProvider()
	tp.RegisterSpanProcessor(recorder)
	t.Cleanup(func() { tp.UnregisterSpanProcessor(recorder) })

	tool := NewTool[shoutIn, shoutIn](New(newTestGenkit(), newFakeRunner(nil), WithName("tools")), "shout", "")
	res, err := tool.RunJSONWithTelemetry(context.Background(), json.RawMessage(`{"text":"x"}`), nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range recorder.Ended() {
		if s.SpanContext().TraceID().String() != res.TraceId || s.Name() != "shout" {
			continue
		}
		attrs := map[string]string{}
		for _, kv := range s.Attributes() {
			attrs[string(kv.Key)] = kv.Value.Emit()
		}
		if attrs[boxAttr] != "tools" || attrs[boxTraceIDAttr] != "box-trace-"+SingletonKey {
			t.Errorf("span attributes = %v, want %s=tools and %s set", attrs, boxAttr, boxTraceIDAttr)
		}
		return
	}
	t.Errorf("no caller-side span in trace %s", res.TraceId)
}

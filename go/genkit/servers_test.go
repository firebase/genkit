// Copyright 2024 Google LLC
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

package genkit

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/action"
	"github.com/firebase/genkit/go/internal/atype"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
	"github.com/invopop/jsonschema"
)

func inc(_ context.Context, x int, _ noStream) (int, error) {
	return x + 1, nil
}

func dec(_ context.Context, x int, _ noStream) (int, error) {
	return x - 1, nil
}

func TestDevServer(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	core.DefineActionInRegistry(r, "devServer", "inc", atype.Custom, map[string]any{
		"foo": "bar",
	}, nil, inc)
	core.DefineActionInRegistry(r, "devServer", "dec", atype.Custom, map[string]any{
		"bar": "baz",
	}, nil, dec)
	srv := httptest.NewServer(newDevServeMux(r))
	defer srv.Close()

	t.Run("runAction", func(t *testing.T) {
		body := `{"key": "/custom/devServer/inc", "input": 3}`
		res, err := http.Post(srv.URL+"/api/runAction", "application/json", strings.NewReader(body))
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if res.StatusCode != 200 {
			t.Fatalf("got status %d, wanted 200", res.StatusCode)
		}
		got, err := readJSON[runActionResponse](res.Body)
		if err != nil {
			t.Fatal(err)
		}
		if g, w := string(got.Result), "4"; g != w {
			t.Errorf("got %q, want %q", g, w)
		}
		tid := got.Telemetry.TraceID
		if len(tid) != 32 {
			t.Errorf("trace ID is %q, wanted 32-byte string", tid)
		}
		checkActionTrace(t, r, tid, "inc")
	})
	t.Run("list actions", func(t *testing.T) {
		res, err := http.Get(srv.URL + "/api/actions")
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if res.StatusCode != 200 {
			t.Fatalf("got status %d, wanted 200", res.StatusCode)
		}
		got, err := readJSON[map[string]action.Desc](res.Body)
		if err != nil {
			t.Fatal(err)
		}
		want := map[string]action.Desc{
			"/custom/devServer/inc": {
				Key:          "/custom/devServer/inc",
				Name:         "devServer/inc",
				InputSchema:  &jsonschema.Schema{Type: "integer"},
				OutputSchema: &jsonschema.Schema{Type: "integer"},
				Metadata:     map[string]any{"foo": "bar"},
			},
			"/custom/devServer/dec": {
				Key:          "/custom/devServer/dec",
				InputSchema:  &jsonschema.Schema{Type: "integer"},
				OutputSchema: &jsonschema.Schema{Type: "integer"},
				Name:         "devServer/dec",
				Metadata:     map[string]any{"bar": "baz"},
			},
		}
		diff := cmp.Diff(want, got, cmpopts.IgnoreUnexported(jsonschema.Schema{}))
		if diff != "" {
			t.Errorf("mismatch (-want, +got):\n%s", diff)
		}
	})
	t.Run("list traces", func(t *testing.T) {
		res, err := http.Get(srv.URL + "/api/envs/dev/traces")
		if err != nil {
			t.Fatal(err)
		}
		if res.StatusCode != 200 {
			t.Fatalf("got status %d, wanted 200", res.StatusCode)
		}
		_, err = readJSON[listTracesResult](res.Body)
		if err != nil {
			t.Fatal(err)
		}
		// We may have any result, including internal.Zero traces, so don't check anything else.
	})
}

func TestProdServer(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	defineFlow(r, "inc", func(_ context.Context, i int, _ noStream) (int, error) {
		return i + 1, nil
	})
	srv := httptest.NewServer(newFlowServeMux(r, nil))
	defer srv.Close()

	check := func(t *testing.T, input string, wantStatus, wantResult int) {
		res, err := http.Post(srv.URL+"/inc", "application/json", strings.NewReader(input))
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if g, w := res.StatusCode, wantStatus; g != w {
			t.Fatalf("status: got %d, want %d", g, w)
		}
		if res.StatusCode != 200 {
			return
		}
		type resultType struct {
			Result int
		}
		got, err := readJSON[resultType](res.Body)
		if err != nil {
			t.Fatal(err)
		}
		if g, w := got.Result, wantResult; g != w {
			t.Errorf("result: got %d, want %d", g, w)
		}
	}

	t.Run("ok", func(t *testing.T) { check(t, "2", 200, 3) })
	t.Run("bad", func(t *testing.T) { check(t, "true", 400, 0) })
}

func checkActionTrace(t *testing.T, reg *registry.Registry, tid, name string) {
	ts := reg.LookupTraceStore(registry.EnvironmentDev)
	td, err := ts.Load(context.Background(), tid)
	if err != nil {
		t.Fatal(err)
	}
	rootSpan := findRootSpan(t, td.Spans)
	want := &tracing.SpanData{
		TraceID:                 tid,
		DisplayName:             "dev-run-action-wrapper",
		SpanKind:                "INTERNAL",
		SameProcessAsParentSpan: tracing.BoolValue{Value: true},
		Status:                  tracing.Status{Code: 0},
		InstrumentationLibrary: tracing.InstrumentationLibrary{
			Name:    "genkit-tracer",
			Version: "v1",
		},
		Attributes: map[string]any{
			"genkit:name":                         "dev-run-action-wrapper",
			"genkit:input":                        "3",
			"genkit:isRoot":                       true,
			"genkit:path":                         "/dev-run-action-wrapper",
			"genkit:output":                       "4",
			"genkit:metadata:genkit-dev-internal": "true",
			"genkit:state":                        "success",
		},
	}
	diff := cmp.Diff(want, rootSpan, cmpopts.IgnoreFields(tracing.SpanData{}, "SpanID", "StartTime", "EndTime"))
	if diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}

// findRootSpan finds the root span in spans.
// It also verifies that it is unique.
func findRootSpan(t *testing.T, spans map[string]*tracing.SpanData) *tracing.SpanData {
	t.Helper()
	var root *tracing.SpanData
	for _, sd := range spans {
		if sd.ParentSpanID == "" {
			if root != nil {
				t.Fatal("more than one root span")
			}
			if g, w := sd.Attributes["genkit:isRoot"], true; g != w {
				t.Errorf("root span genkit:isRoot attr = %v, want %v", g, w)
			}
			root = sd
		}
	}
	if root == nil {
		t.Fatal("no root span")
	}
	return root
}

func readJSON[T any](r io.Reader) (T, error) {
	var x T
	if err := json.NewDecoder(r).Decode(&x); err != nil {
		return x, err
	}
	return x, nil
}

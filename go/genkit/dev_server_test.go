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
	"maps"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

func dec(_ context.Context, x int) (int, error) {
	return x - 1, nil
}

func TestDevServer(t *testing.T) {
	r, err := newRegistry()
	if err != nil {
		t.Fatal(err)
	}
	r.registerAction("test", "devServer", NewAction("inc", inc))
	r.registerAction("test", "devServer", NewAction("dec", dec))
	srv := httptest.NewServer(newDevServerMux(r))
	defer srv.Close()

	t.Run("runAction", func(t *testing.T) {
		body := `{"key": "/test/devServer/inc", "input": 3}`
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
		got, err := readJSON[map[string]actionDesc](res.Body)
		if err != nil {
			t.Fatal(err)
		}
		md := map[string]any{"inputSchema": nil, "outputSchema": nil}
		want := map[string]actionDesc{
			"/test/devServer/dec": {Key: "/test/devServer/dec", Name: "dec", Metadata: md},
			"/test/devServer/inc": {Key: "/test/devServer/inc", Name: "inc", Metadata: md},
		}
		if !maps.EqualFunc(got, want, actionDesc.equal) {
			t.Errorf("\n got  %v\nwant %v", got, want)
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
		// We may have any result, including zero traces, so don't check anything else.
	})
}

func checkActionTrace(t *testing.T, reg *registry, tid, name string) {
	ts := reg.lookupTraceStore(EnvironmentDev)
	td, err := ts.Load(context.Background(), tid)
	if err != nil {
		t.Fatal(err)
	}
	rootSpan := findRootSpan(t, td.Spans)
	want := &SpanData{
		TraceID:                 tid,
		DisplayName:             "dev-run-action-wrapper",
		SpanKind:                "INTERNAL",
		SameProcessAsParentSpan: boolValue{Value: true},
		Status:                  Status{Code: 0},
		InstrumentationLibrary: InstrumentationLibrary{
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
	diff := cmp.Diff(want, rootSpan, cmpopts.IgnoreFields(SpanData{}, "SpanID", "StartTime", "EndTime"))
	if diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}

// findRootSpan finds the root span in spans.
// It also verifies that it is unique.
func findRootSpan(t *testing.T, spans map[string]*SpanData) *SpanData {
	t.Helper()
	var root *SpanData
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

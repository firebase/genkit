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

package core

import (
	"cmp"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"path/filepath"
	"reflect"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/firebase/genkit/go/internal"
	"golang.org/x/exp/maps"
)

// conformanceTest describes a JSON format for language-independent testing
// of genkit flows ("conformance testing" for lack of a better term).
//
// All flows are functions from string to string.
type conformanceTest struct {
	// Flow definition
	Name     string    // name of the flow
	Commands []command // a list of commands comprising the body of the flow

	// Action input
	// This is the input field in the body of the /api/runAction route.
	// The key field is constructed from the flow name.
	Input json.RawMessage

	// Expected output
	// These will unmarshal into untyped JSON (map[string]any, etc.), which
	// facilitates comparing them in a general way. See compareJSON, below.
	Result any
	Trace  any
}

// A command is one function to run as part of a flow.
type command struct {
	// Append appends its value to the input.
	Append *string
	// Run calls [Run] with the given name and a function whose body executes the
	// given command.
	Run *struct {
		Name    string
		Command *command
	}
}

func (c *command) run(ctx context.Context, input string) (string, error) {
	switch {
	case c.Append != nil:
		return input + *c.Append, nil
	case c.Run != nil:
		return InternalRun(ctx, c.Run.Name, func() (string, error) {
			return c.Run.Command.run(ctx, input)
		})
	default:
		return "", errors.New("unknown command")
	}
}

func TestFlowConformance(t *testing.T) {
	testFiles, err := filepath.Glob(filepath.FromSlash("testdata/conformance/*.json"))
	if err != nil {
		t.Fatal(err)
	}
	if len(testFiles) == 0 {
		t.Fatal("did not find any test files")
	}
	for _, filename := range testFiles {
		t.Run(strings.TrimSuffix(filepath.Base(filename), ".json"), func(t *testing.T) {
			var test conformanceTest
			if err := internal.ReadJSONFile(filename, &test); err != nil {
				t.Fatal(err)
			}
			// Each test uses its own registry to avoid interference.
			r, err := newRegistry()
			if err != nil {
				t.Fatal(err)
			}
			_ = defineFlow(r, test.Name, flowFunction(test.Commands))
			key := fmt.Sprintf("/flow/%s", test.Name)
			resp, err := runAction(context.Background(), r, key, test.Input, nil)
			if err != nil {
				t.Fatal(err)
			}
			var result any
			if err := json.Unmarshal(resp.Result, &result); err != nil {
				t.Fatal(err)
			}
			if diff := compareJSON(result, test.Result); diff != "" {
				t.Errorf("result:\n%s", diff)
			}

			if test.Trace == nil {
				return
			}
			ts := r.lookupTraceStore(EnvironmentDev)
			var gotTrace any
			if err := ts.LoadAny(resp.Telemetry.TraceID, &gotTrace); err != nil {
				t.Fatal(err)
			}
			renameSpans(t, gotTrace)
			renameSpans(t, test.Trace)
			if diff := compareJSON(gotTrace, test.Trace); diff != "" {
				t.Errorf("trace:\n%s", diff)
			}
		})
	}
}

// flowFunction returns a function that runs the list of commands.
func flowFunction(commands []command) Func[string, string, struct{}] {
	return func(ctx context.Context, input string, cb NoStream) (string, error) {
		result := input
		var err error
		for i, cmd := range commands {
			if i > 0 {
				// Pause between commands to ensure the trace start times are different.
				// See renameSpans for why this is necessary.
				time.Sleep(5 * time.Millisecond)
			}
			result, err = cmd.run(ctx, result)
			if err != nil {
				return "", err
			}
		}
		return result, nil
	}
}

// renameSpans is given a trace, one of whose fields is a map from span ID to span.
// It changes the span map keys to s0, s1, ... in order of the span start time,
// as well as references to those IDs within the spans.
// This makes it possible to compare two span maps with different span IDs.
func renameSpans(t *testing.T, trace any) {
	spans := trace.(map[string]any)["spans"].(map[string]any)
	type item struct {
		id string
		t  float64
	}
	var items []item
	startTimes := map[float64]bool{}
	for id, span := range spans {
		m := span.(map[string]any)
		startTime := m["startTime"].(float64)
		if startTimes[startTime] {
			t.Fatal("duplicate start times")
		}
		startTimes[startTime] = true
		// Delete startTimes because we don't want to compare them.
		delete(m, "startTime")
		items = append(items, item{id, startTime})
	}
	slices.SortFunc(items, func(i1, i2 item) int {
		return cmp.Compare(i1.t, i2.t)
	})
	oldIDToNew := map[string]string{}
	for i, item := range items {
		oldIDToNew[item.id] = fmt.Sprintf("s%03d", i)
	}
	// Change old spanIDs to new.
	// We cannot range over the map itself, because we change its keys in the loop.
	for _, oldID := range maps.Keys(spans) {
		span := spans[oldID].(map[string]any)
		newID := oldIDToNew[oldID]
		if newID == "" {
			t.Fatalf("missing id: %q", oldID)
		}
		spans[newID] = span
		delete(spans, oldID)
		// A span references it own span ID and possibly its parent's.
		span["spanId"] = oldIDToNew[span["spanId"].(string)]
		if pid, ok := span["parentSpanId"]; ok {
			span["parentSpanId"] = oldIDToNew[pid.(string)]
		}
	}
}

// compareJSON compares two unmarshaled JSON values.
// Each must be nil or of type string, float64, bool, []any or map[string]any;
// these are the types used by json.Unmarshal when there is no type information
// (that is, when unmarshaling into a value of type any).
// For maps, only keys in the "want" map are examined; any extra keys in the "got"
// map are ignored.
// If the "want" value is the string "$ANYTHING", then the corresponding "got" value can
// be any string.
// If a "want" map key is "_comment", no comparison is done.
func compareJSON(got, want any) string {
	var problems []string

	add := func(prefix, format string, args ...any) {
		problems = append(problems, prefix+": "+fmt.Sprintf(format, args...))
	}

	var compareJSON1 func(prefix string, got, want any)
	compareJSON1 = func(prefix string, got, want any) {
		if want == nil {
			if got != nil {
				add(prefix, "got %v, want nil", got)
			}
			return
		}
		if got == nil {
			add(prefix, "got nil, want %v", want)
			return
		}
		if gt, wt := reflect.TypeOf(got), reflect.TypeOf(want); gt != wt {
			add(prefix, "got type %s, want %s", gt, wt)
			return
		}
		switch want := want.(type) {
		case string, float64, bool:
			if got != want && want != "$ANYTHING" {
				add(prefix, "\ngot  %v\nwant %v", got, want)
			}
		case []any:
			got := got.([]any)
			if len(got) != len(want) {
				add(prefix, "lengths differ")
				return
			}
			for i, g := range got {
				compareJSON1(fmt.Sprintf("%s[%d]", prefix, i), g, want[i])
			}

		case map[string]any:
			got := got.(map[string]any)
			for k, wv := range want {
				if k == "_comment" {
					continue
				}
				gv, ok := got[k]
				if !ok {
					add(prefix, "missing key: %q", k)
				} else {
					compareJSON1(prefix+"."+k, gv, wv)
				}
			}
		default:
			add(prefix, "unknown type %T", want)
		}
	}

	compareJSON1("", got, want)
	return strings.Join(problems, "\n")
}

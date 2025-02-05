// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package tracing

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestTraceJSON(t *testing.T) {
	// We want to compare a JSON trace produced by the genkit javascript code,
	// in testdata/trace.json, with our own JSON output.
	// If we just compared the text of the file, it would probably fail because
	// the order in which fields of a JSON object are written could differ.
	// We can't just read back in what we wrote; that only proves that our
	// implementation is consistent, not that it matches the js one.
	// So we unmarshal the JSON into a map, and compare the maps.
	// TODO: increase coverage. The stored trace is missing some structs.

	// Unmarshal the js trace into our TraceData.
	jsBytes, err := os.ReadFile(filepath.Join("testdata", "trace.json"))
	if err != nil {
		t.Fatal(err)
	}
	var td Data
	if err := json.Unmarshal(jsBytes, &td); err != nil {
		t.Fatal(err)
	}

	// Marshal that TraceData.
	goBytes, err := json.Marshal(td)
	if err != nil {
		t.Fatal(err)
	}

	// Unmarshal both JSON objects into maps.
	var jsMap, goMap map[string]any
	if err := json.Unmarshal(jsBytes, &jsMap); err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(goBytes, &goMap); err != nil {
		t.Fatal(err)
	}

	// Compare the maps.
	if diff := cmp.Diff(jsMap, goMap); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
	ensureAllSpanDataFieldsArePresent(t, td, goMap)
}

// ensureAllSpanDataFieldsArePresent checks that every non-zero field in SpanData
// (by its json tag) is present in the marshaled JSON. Fields with `,omitempty`
// that are zero/empty are allowed to be omitted.
func ensureAllSpanDataFieldsArePresent(t *testing.T, data Data, jsonMap map[string]any) {
	spans, ok := jsonMap["spans"].(map[string]any)
	if !ok {
		t.Errorf("expected 'spans' to be a map, but got %T", jsonMap["spans"])
		return
	}

	spanDataType := reflect.TypeOf(SpanData{})

	for spanKey, spanVal := range spans {
		// Retrieve the SpanData struct from `data` so we can reflect on actual field values.
		spanStruct := data.Spans[spanKey]
		if spanStruct == nil {
			t.Errorf("no SpanData found for %q in the original Data struct", spanKey)
			continue
		}

		spanMap, ok := spanVal.(map[string]any)
		if !ok {
			t.Errorf("span %q expected to be a map, got %T", spanKey, spanVal)
			continue
		}

		// Check each exported field in SpanData.
		spanValReflect := reflect.ValueOf(*spanStruct)
		for i := 0; i < spanDataType.NumField(); i++ {
			field := spanDataType.Field(i)
			tag := field.Tag.Get("json")
			if tag == "" || tag == "-" {
				continue // no JSON tag or explicitly ignored
			}
			jsonKey := strings.SplitN(tag, ",", 2)[0]

			// If the JSON key is empty (unlikely), skip
			if jsonKey == "" {
				continue
			}

			// Check if field has ",omitempty"
			omitempty := false
			if strings.Contains(tag, ",omitempty") {
				omitempty = true
			}

			// Get the actual value of that field in the struct
			fieldVal := spanValReflect.Field(i)

			// If the field is zero and has omitempty, skip the check
			if omitempty && isZeroValue(fieldVal) {
				continue
			}

			// Otherwise, we expect the field to be present in the JSON map.
			if _, present := spanMap[jsonKey]; !present {
				t.Errorf("span %q is missing non-zero field %q in the JSON output", spanKey, jsonKey)
			}
		}
	}
}

// isZeroValue tells if a reflect.Value is the "zero" value for its type.
// Go 1.13+ provides v.IsZero(), but let's be explicit for clarity.
func isZeroValue(v reflect.Value) bool {
	// If v is invalid, it's zero by definition.
	if !v.IsValid() {
		return true
	}

	switch v.Kind() {
	case reflect.Bool:
		return !v.Bool()
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return v.Int() == 0
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64, reflect.Uintptr:
		return v.Uint() == 0
	case reflect.Float32, reflect.Float64:
		return v.Float() == 0
	case reflect.String:
		return v.Len() == 0
	case reflect.Array:
		// For an array, compare each element
		for i := 0; i < v.Len(); i++ {
			if !isZeroValue(v.Index(i)) {
				return false
			}
		}
		return true
	case reflect.Slice, reflect.Map, reflect.Chan, reflect.Func, reflect.Interface, reflect.Pointer:
		return v.IsNil()
	case reflect.Struct:
		// For a struct, either use IsZero (Go 1.13+) or compare each field
		// We'll use v.IsZero() if available. If not, we can do a manual check.
		return v.IsZero()
	}
	return false
}

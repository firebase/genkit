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
	"slices"
	"strings"
	"testing"
)

func dec(_ context.Context, x int) (int, error) {
	return x - 1, nil
}

func TestDevServer(t *testing.T) {
	RegisterAction("test", "inc", NewAction("inc", inc))
	RegisterAction("test", "dec", NewAction("dec", dec))
	srv := httptest.NewServer(newDevServerMux())
	defer srv.Close()

	t.Run("runAction", func(t *testing.T) {
		body := `{"key": "/test/inc", "input": 3}`
		res, err := http.Post(srv.URL+"/api/runAction", "application/json", strings.NewReader(body))
		if err != nil {
			t.Fatal(err)
		}
		defer res.Body.Close()
		if res.StatusCode != 200 {
			t.Fatalf("got status %d, wanted 200", res.StatusCode)
		}
		got, err := readJSON[int](res.Body)
		if err != nil {
			t.Fatal(err)
		}
		want := 4
		if got != want {
			t.Errorf("got %d, want %d", got, want)
		}
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
		got, err := readJSON[[]actionDesc](res.Body)
		if err != nil {
			t.Fatal(err)
		}
		want := []actionDesc{
			{Key: "/test/dec", Name: "dec"},
			{Key: "/test/inc", Name: "inc"},
		}
		if !slices.EqualFunc(got, want, actionDesc.equal) {
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

func readJSON[T any](r io.Reader) (T, error) {
	var x T
	if err := json.NewDecoder(r).Decode(&x); err != nil {
		return x, err
	}
	return x, nil
}

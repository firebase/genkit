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
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestDevServer(t *testing.T) {
	RegisterAction("test", "inc", NewAction("inc", inc))
	srv := httptest.NewServer(newDevServerMux())
	defer srv.Close()

	body := `{"key": "/test/inc", "input": 3}`
	res, err := http.Post(srv.URL+"/api/runAction", "application/json", strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		t.Fatalf("got status %d, wanted 200", res.StatusCode)
	}
	data, err := io.ReadAll(res.Body)
	if err != nil {
		t.Fatal(err)
	}
	got := string(data)
	want := `4`
	if got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

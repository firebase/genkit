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

package tests

import (
	"errors"
	"net/http"
	"net/http/httptest"
)

// MockRoundTripper is a RoundTripper whose responses can be set by the program.
// It is configured exactly like a ServeMux: by registering http.Handlers with
// patterns. When a request is received, the matching handler is run and
// its response is returned.
//
// This type is a convenience; the same result can be achieved by registering
// handlers with an httptest.Server and using its client. This avoids the
// (local) network round trip.
type MockRoundTripper struct {
	mux http.ServeMux
}

// Handle registers a handle with the MockRoundTripper associated with the given pattern.
func (rt *MockRoundTripper) Handle(pattern string, handler http.Handler) {
	rt.mux.Handle(pattern, handler)
}

func (rt *MockRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
	h, pat := rt.mux.Handler(req)
	if pat == "" {
		return nil, errors.New("no matching handler matches")
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	return w.Result(), nil
}

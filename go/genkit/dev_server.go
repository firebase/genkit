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

// This file implements a server used for development.
// The genkit CLI sends requests to it.
//
// See js/common/src/reflectionApi.ts.

import (
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"sync/atomic"
)

// StartDevServer starts the development server (reflection API) at the given address.
// If addr is empty, it uses port 3100.
// StartDevServer always returns a non-nil error, the one returned by http.ListenAndServe.
func StartDevServer(addr string) error {
	if addr == "" {
		addr = "localhost:3100"
	}
	mux := newDevServerMux()
	slog.Info("listening", "addr", addr)
	return http.ListenAndServe(addr, mux)
}

func newDevServerMux() *http.ServeMux {
	mux := http.NewServeMux()
	handle(mux, "POST /api/runAction", handleRunAction)
	handle(mux, "GET /api/actions", handleListActions)
	return mux
}

// requestID is a unique ID for each request.
var requestID atomic.Int64

// handle registers pattern on mux with an http.Handler that calls f.
// If f returns a non-nil error, the handler calls http.Error.
// If the error is an httpError, the code it contains is used as the status code;
// otherwise a 500 status is used.
func handle(mux *http.ServeMux, pattern string, f func(w http.ResponseWriter, r *http.Request) error) {
	mux.HandleFunc(pattern, func(w http.ResponseWriter, r *http.Request) {
		id := requestID.Add(1)
		// Create a logger that always outputs the requestID, and store it in the request context.
		log := slog.Default().With("reqID", id)
		log.Info("request start",
			"method", r.Method,
			"path", r.URL.Path)
		var err error
		defer func() {
			if err != nil {
				log.Error("request end", "err", err)
			} else {
				log.Info("request end")
			}
		}()
		err = f(w, r)
		if err != nil {
			// If the error is an httpError, serve the status code it contains.
			// Otherwise, assume this is an unexpected error and serve a 500.
			var herr *httpError
			if errors.As(err, &herr) {
				http.Error(w, herr.Error(), herr.code)
			} else {
				http.Error(w, err.Error(), http.StatusInternalServerError)
			}
		}
	})
}

type httpError struct {
	code int
	err  error
}

func (e *httpError) Error() string {
	return fmt.Sprintf("%s: %s", http.StatusText(e.code), e.err)
}

// handleRunAction looks up an action by name in the registry, runs it with the
// provded JSON input, and writes back the JSON-marshaled request.
func handleRunAction(w http.ResponseWriter, r *http.Request) error {
	var body struct {
		Key   string          `json:"key"`
		Input json.RawMessage `json:"input"`
	}
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		return &httpError{http.StatusBadRequest, err}
	}
	action := lookupAction(body.Key)
	logger(r.Context()).Debug("bodyKey", "k", body.Key)
	if action == nil {
		return &httpError{http.StatusNotFound, errors.New("no action with that ID")}
	}
	output, err := action.runJSON(r.Context(), body.Input)
	if err != nil {
		return err
	}
	_, err = w.Write(output)
	if err != nil {
		logger(r.Context()).Error("writing runAction output", "err", err)
	}
	return nil
}

// handleListActions lists all the registered actions.
func handleListActions(w http.ResponseWriter, r *http.Request) error {
	descs := listActions()
	data, err := json.MarshalIndent(descs, "", "    ")
	if err != nil {
		return err
	}
	_, err = w.Write(data)
	if err != nil {
		logger(r.Context()).Error("writing actions output", "err", err)
	}
	return nil
}

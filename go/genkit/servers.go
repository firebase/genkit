// Copyright 2025 Google LLC
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

package genkit

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"maps"
	"net/http"
	"strconv"
	"strings"
	"sync/atomic"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
)

type HandlerOption interface {
	apply(params *handlerParams)
}

// handlerParams are the parameters for an action HTTP handler.
type handlerParams struct {
	ContextProviders []core.ContextProvider // Providers for action context that may be used during runtime.
}

// apply applies the options to the handler params.
func (p *handlerParams) apply(params *handlerParams) {
	if params.ContextProviders != nil {
		panic("genkit.WithContextProviders: cannot set ContextProviders more than once")
	}
	params.ContextProviders = p.ContextProviders
}

// requestID is a unique ID for each request.
var requestID atomic.Int64

// WithContextProviders adds providers for action context that may be used during runtime.
// They are called in the order added and may overwrite previous context.
func WithContextProviders(ctxProviders ...core.ContextProvider) HandlerOption {
	return &handlerParams{ContextProviders: ctxProviders}
}

// Handler returns an HTTP handler function that serves the action with the provided options.
//
// Example:
//
//	genkit.Handler(g, genkit.WithContextProviders(func(ctx context.Context, req core.RequestData) (core.ActionContext, error) {
//		return core.ActionContext{"myKey": "myValue"}, nil
//	}))
func Handler(a core.Action, opts ...HandlerOption) http.HandlerFunc {
	params := &handlerParams{}
	for _, opt := range opts {
		opt.apply(params)
	}

	return wrapHandler(handler(a, params))
}

// wrapHandler wraps an HTTP handler function with common logging and error handling.
func wrapHandler(h func(http.ResponseWriter, *http.Request) error) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		log := slog.Default().With("reqID", requestID.Add(1))
		log.Debug("request start", "method", r.Method, "path", r.URL.Path)

		var err error
		defer func() {
			if err != nil {
				log.Error("request end", "err", err)
			} else {
				log.Debug("request end")
			}
		}()

		if err = h(w, r); err != nil {
			var herr *core.GenkitError
			if errors.As(err, &herr) {
				http.Error(w, herr.Error(), core.HTTPStatusCode(herr.Status))
			} else {
				http.Error(w, err.Error(), http.StatusInternalServerError)
			}
		}
	}
}

// handler returns an HTTP handler function that serves the action with the provided params. Responses are written in server-sent events (SSE) format.
func handler(a core.Action, params *handlerParams) func(http.ResponseWriter, *http.Request) error {
	return func(w http.ResponseWriter, r *http.Request) error {
		if a == nil {
			return errors.New("action is nil; cannot serve")
		}

		var body struct {
			Data json.RawMessage `json:"data"`
		}
		if r.Body != nil && r.ContentLength > 0 {
			defer r.Body.Close()
			if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
				return core.NewPublicError(core.INVALID_ARGUMENT, err.Error(), nil)
			}
		}

		stream, err := parseBoolQueryParam(r, "stream")
		if err != nil {
			return err
		}
		stream = stream || r.Header.Get("Accept") == "text/event-stream"

		var callback streamingCallback[json.RawMessage]
		if stream {
			w.Header().Set("Content-Type", "text/event-stream")
			w.Header().Set("Cache-Control", "no-cache")
			w.Header().Set("Connection", "keep-alive")
			w.Header().Set("Transfer-Encoding", "chunked")
			callback = func(ctx context.Context, msg json.RawMessage) error {
				_, err := fmt.Fprintf(w, "data: {\"message\": %s}\n\n", msg)
				if err != nil {
					return err
				}
				if f, ok := w.(http.Flusher); ok {
					f.Flush()
				}
				return nil
			}
		} else {
			w.Header().Set("Content-Type", "application/json")
		}

		ctx := r.Context()
		if params.ContextProviders != nil {
			for _, ctxProvider := range params.ContextProviders {
				headers := make(map[string]string, len(r.Header))
				for k, v := range r.Header {
					headers[strings.ToLower(k)] = strings.Join(v, " ")
				}

				actionCtx, err := ctxProvider(ctx, core.RequestData{
					Method:  r.Method,
					Headers: headers,
					Input:   body.Data,
				})
				if err != nil {
					logger.FromContext(ctx).Error("error providing action context from request", "err", err)
					return err
				}

				if existing := core.FromContext(ctx); existing != nil {
					maps.Copy(existing, actionCtx)
					actionCtx = existing
				}
				ctx = core.WithActionContext(ctx, actionCtx)
			}
		}

		out, err := a.RunJSON(ctx, body.Data, callback)
		if err != nil {
			if stream {
				_, err = fmt.Fprintf(w, "data: {\"error\": {\"status\": \"INTERNAL\", \"message\": \"stream flow error\", \"details\": \"%v\"}}\n\n", err)
				return err
			}
			return err
		}
		if stream {
			_, err = fmt.Fprintf(w, "data: {\"result\": %s}\n\n", out)
			return err
		}

		_, err = fmt.Fprintf(w, "{\"result\": %s}\n", out)
		return err
	}
}

func parseBoolQueryParam(r *http.Request, name string) (bool, error) {
	b := false
	if s := r.FormValue(name); s != "" {
		var err error
		b, err = strconv.ParseBool(s)
		if err != nil {
			return false, core.NewPublicError(core.INVALID_ARGUMENT, err.Error(), nil)
		}
	}
	return b, nil
}

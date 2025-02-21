// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package genkit

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync/atomic"
	"syscall"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/internal/base"
)

type HandlerOption = func(params *handlerParams)

type handlerParams struct {
	ContextProvider core.ContextProvider
}

// requestID is a unique ID for each request.
var requestID atomic.Int64

// WithContextProvider sets the context provider for the handler.
func WithContextProvider(ctxProvider core.ContextProvider) HandlerOption {
	return func(params *handlerParams) {
		if params.ContextProvider != nil {
			panic("genkit.WithContextProvider: cannot set ContextProvider more than once")
		}
		params.ContextProvider = ctxProvider
	}
}

// Handler returns an HTTP handler function that serves the action with the provided options.
func Handler(a Action, opts ...HandlerOption) http.HandlerFunc {
	params := &handlerParams{}
	for _, opt := range opts {
		opt(params)
	}
	return wrapHandler(handler(a, params))
}

// StartServer starts a new HTTP server and manages its lifecycle.
func StartServer(ctx context.Context, addr string, mux *http.ServeMux) error {
	ctx, cancel := signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)
	defer cancel()

	srv := &http.Server{
		Addr:    addr,
		Handler: mux,
	}

	errChan := make(chan error, 1)

	go func() {
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errChan <- fmt.Errorf("server error: %w", err)
		}
		cancel()
	}()

	select {
	case err := <-errChan:
		return err
	case <-ctx.Done():
		if err := srv.Shutdown(ctx); err != nil {
			return fmt.Errorf("failed to shutdown server: %w", err)
		}
	}
	return nil
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
			var herr *base.HTTPError
			if errors.As(err, &herr) {
				http.Error(w, herr.Error(), herr.Code)
			} else {
				http.Error(w, err.Error(), http.StatusInternalServerError)
			}
		}
	}
}

// handler returns an HTTP handler function that serves the action with the provided params. Responses are written in server-sent events (SSE) format.
func handler(a Action, params *handlerParams) func(http.ResponseWriter, *http.Request) error {
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
				return &base.HTTPError{Code: http.StatusBadRequest, Err: err}
			}
		}

		stream, err := parseBoolQueryParam(r, "stream")
		if err != nil {
			return err
		}
		stream = stream || r.Header.Get("Accept") == "text/event-stream"

		var callback streamingCallback[json.RawMessage]
		if stream {
			w.Header().Set("Content-Type", "text/plain")
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
		}

		ctx := r.Context()
		if params.ContextProvider != nil {
			headers := make(map[string]string, len(r.Header))
			for k, v := range r.Header {
				headers[strings.ToLower(k)] = strings.Join(v, " ")
			}

			actionCtx, err := params.ContextProvider(ctx, core.RequestData{
				Method:  r.Method,
				Headers: headers,
				Input:   body.Data,
			})
			if err != nil {
				logger.FromContext(ctx).Error("error providing action runtime context from request", "err", err)
				return &base.HTTPError{Code: http.StatusUnauthorized, Err: err}
			}

			ctx = core.WithActionContext(ctx, actionCtx)
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

		_, err = fmt.Fprintf(w, `{"result": %s}\n`, out)
		return err
	}
}

func parseBoolQueryParam(r *http.Request, name string) (bool, error) {
	b := false
	if s := r.FormValue(name); s != "" {
		var err error
		b, err = strconv.ParseBool(s)
		if err != nil {
			return false, &base.HTTPError{Code: http.StatusBadRequest, Err: err}
		}
	}
	return b, nil
}

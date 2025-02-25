// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package genkit

import (
	"context"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/core"
)

func FakeContextProvider(ctx context.Context, req core.RequestData) (core.ActionContext, error) {
	return core.ActionContext{
		"test": "action-context-value",
	}, nil
}

func TestHandler(t *testing.T) {
	g, err := Init(context.Background())
	if err != nil {
		t.Fatalf("failed to initialize Genkit: %v", err)
	}

	echoFlow := DefineFlow(g, "echo", func(ctx context.Context, input string) (string, error) {
		return input, nil
	})

	errorFlow := DefineFlow(g, "error", func(ctx context.Context, input string) (string, error) {
		return "", errors.New("flow error")
	})

	contextReaderFlow := DefineFlow(g, "contextReader", func(ctx context.Context, input []string) (string, error) {
		actionCtx := core.FromContext(ctx)
		if actionCtx == nil {
			return "", errors.New("no action context")
		}

		if len(input) == 0 {
			return "", nil
		}

		var values []string
		for _, key := range input {
			value, ok := actionCtx[key]
			if !ok {
				return "", fmt.Errorf("action context key %q not found", key)
			}

			strValue, ok := value.(string)
			if !ok {
				return "", fmt.Errorf("action context value for key %q is not a string", key)
			}

			values = append(values, strValue)
		}

		return strings.Join(values, ","), nil
	})

	t.Run("basic handler", func(t *testing.T) {
		handler := Handler(echoFlow)

		req := httptest.NewRequest("POST", "/", strings.NewReader(`{"data":"test-input"}`))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		handler(w, req)

		resp := w.Result()
		body, _ := io.ReadAll(resp.Body)

		if resp.StatusCode != http.StatusOK {
			t.Errorf("want status code %d, got %d", http.StatusOK, resp.StatusCode)
		}

		if !strings.Contains(string(body), `"test-input"`) {
			t.Errorf("want response to contain test-input, got %q", string(body))
		}
	})

	t.Run("action error", func(t *testing.T) {
		handler := Handler(errorFlow)

		req := httptest.NewRequest("POST", "/", strings.NewReader(`{"data":"test-input"}`))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		handler(w, req)

		resp := w.Result()
		body, _ := io.ReadAll(resp.Body)

		if resp.StatusCode != http.StatusInternalServerError {
			t.Errorf("want status code %d, got %d", http.StatusInternalServerError, resp.StatusCode)
		}

		expected := "flow error\n"
		if string(body) != expected {
			t.Errorf("want response to contain flow error, got %q", string(body))
		}
	})

	t.Run("invalid JSON", func(t *testing.T) {
		handler := Handler(echoFlow)

		req := httptest.NewRequest("POST", "/", strings.NewReader(`{"data":invalid-json}`))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		handler(w, req)

		resp := w.Result()
		body, _ := io.ReadAll(resp.Body)

		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("want status code %d, got %d", http.StatusBadRequest, resp.StatusCode)
		}

		if !strings.Contains(string(body), "invalid character") {
			t.Errorf("want error about invalid JSON, got %q", string(body))
		}
	})

	t.Run("with context provider", func(t *testing.T) {
		handler := Handler(contextReaderFlow, WithContextProviders(FakeContextProvider))

		req := httptest.NewRequest("POST", "/", strings.NewReader(`{"data":["test"]}`))
		w := httptest.NewRecorder()

		handler(w, req)

		resp := w.Result()
		body, _ := io.ReadAll(resp.Body)

		if resp.StatusCode != http.StatusOK {
			t.Errorf("want status code %d, got %d", http.StatusOK, resp.StatusCode)
		}

		if !strings.Contains(string(body), "action-context-value") {
			t.Errorf("want response to containaction-context-value, got %q", string(body))
		}
	})

	t.Run("multiple context providers", func(t *testing.T) {
		handler := Handler(contextReaderFlow, WithContextProviders(
			func(ctx context.Context, req core.RequestData) (core.ActionContext, error) {
				return core.ActionContext{"provider1": "value1"}, nil
			},
			func(ctx context.Context, req core.RequestData) (core.ActionContext, error) {
				return core.ActionContext{"provider2": "value2"}, nil
			},
		))

		req := httptest.NewRequest("POST", "/", strings.NewReader(`{"data":["provider1","provider2"]}`))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		handler(w, req)

		resp := w.Result()
		body, _ := io.ReadAll(resp.Body)

		if resp.StatusCode != http.StatusOK {
			t.Errorf("want status code %d, got %d", http.StatusOK, resp.StatusCode)
		}

		if !strings.Contains(string(body), "value1,value2") {
			t.Errorf("want response to contain value1,value2, got %q", string(body))
		}
	})
}

func TestStreamingHandler(t *testing.T) {
	g, err := Init(context.Background())
	if err != nil {
		t.Fatalf("failed to initialize Genkit: %v", err)
	}

	streamingFlow := DefineStreamingFlow(g, "streaming",
		func(ctx context.Context, input string, cb func(context.Context, string) error) (string, error) {
			for _, c := range input {
				if err := cb(ctx, string(c)); err != nil {
					return "", err
				}
			}
			return input + "-end", nil
		})

	errorStreamingFlow := DefineStreamingFlow(g, "errorStreaming",
		func(ctx context.Context, input string, cb func(context.Context, string) error) (string, error) {
			return "", errors.New("streaming error")
		})

	t.Run("streaming response", func(t *testing.T) {
		handler := Handler(streamingFlow)

		req := httptest.NewRequest("POST", "/", strings.NewReader(`{"data":"hello"}`))
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("Accept", "text/event-stream")
		w := httptest.NewRecorder()

		handler(w, req)

		resp := w.Result()
		body, _ := io.ReadAll(resp.Body)

		if resp.StatusCode != http.StatusOK {
			t.Errorf("want status code %d, got %d", http.StatusOK, resp.StatusCode)
		}

		expected := `data: {"message": "h"}

data: {"message": "e"}

data: {"message": "l"}

data: {"message": "l"}

data: {"message": "o"}

data: {"result": "hello-end"}

`
		if string(body) != expected {
			t.Errorf("want streaming body:\n%q\n\nGot:\n%q", expected, string(body))
		}
	})

	t.Run("streaming error", func(t *testing.T) {
		handler := Handler(errorStreamingFlow)

		req := httptest.NewRequest("POST", "/?stream=true", strings.NewReader(`{"data":"test"}`))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()

		handler(w, req)

		resp := w.Result()
		body, _ := io.ReadAll(resp.Body)

		if resp.StatusCode != http.StatusOK { // Note: SSE errors are sent as part of the stream
			t.Errorf("want status code %d, got %d", http.StatusOK, resp.StatusCode)
		}

		expected := `data: {"error": {"status": "INTERNAL", "message": "stream flow error", "details": "streaming error"}}

`
		if string(body) != expected {
			t.Errorf("want error body:\n%q\n\nGot:\n%q", expected, string(body))
		}
	})
}

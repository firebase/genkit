// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package logger provides a context-scoped slog.Logger.
package logger

import (
	"context"
	"log/slog"
	"os"
	"sync"

	"github.com/firebase/genkit/go/internal/base"
)

var (
	logLevel  = slog.LevelDebug
	mu        sync.RWMutex
	loggerKey = base.NewContextKey[*slog.Logger]()
)

// SetLevel sets the global log level
func SetLevel(level slog.Level) {
	mu.Lock()
	defer mu.Unlock()
	logLevel = level
	h := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
		Level: logLevel,
	}))
	slog.SetDefault(h)
}

// GetLevel gets the current global log level
func GetLevel() slog.Level {
	mu.RLock()
	defer mu.RUnlock()
	return logLevel
}

// FromContext returns the Logger in ctx, or the default Logger
// if there is none.
func FromContext(ctx context.Context) *slog.Logger {
	if l := loggerKey.FromContext(ctx); l != nil {
		return l
	}
	return slog.Default()
}

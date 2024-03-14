package genkit

import (
	"context"
	"log/slog"
	"os"
)

func init() {
	// TODO: Remove this. The main program should be responsible for configuring logging.
	// This is just a convenience during development.
	h := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
		Level: slog.LevelDebug,
	}))
	slog.SetDefault(h)
}

var loggerKey = newContextKey[*slog.Logger]()

// logger returns the Logger in ctx, or the default Logger
// if there is none.
func logger(ctx context.Context) *slog.Logger {
	if l := loggerKey.fromContext(ctx); l != nil {
		return l
	}
	return slog.Default()
}

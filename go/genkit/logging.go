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

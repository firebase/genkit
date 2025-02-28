// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// The googlecloud package supports telemetry (tracing, metrics and logging) using
// Google Cloud services.
package googlecloud

import (
	"context"
	"log/slog"

	"cloud.google.com/go/logging"
	"github.com/jba/slog/withsupport"
)

func newHandler(level slog.Leveler, f func(logging.Entry)) *handler {
	if level == nil {
		level = slog.LevelInfo
	}
	return &handler{
		level:       level,
		handleEntry: f,
	}
}

type handler struct {
	level       slog.Leveler
	handleEntry func(logging.Entry)
	goa         *withsupport.GroupOrAttrs
}

func (h *handler) Enabled(ctx context.Context, level slog.Level) bool {
	return level >= h.level.Level()
}

func (h *handler) WithAttrs(as []slog.Attr) slog.Handler {
	h2 := *h
	h2.goa = h2.goa.WithAttrs(as)
	return &h2
}

func (h *handler) WithGroup(name string) slog.Handler {
	h2 := *h
	h2.goa = h2.goa.WithGroup(name)
	return &h2
}

func (h *handler) Handle(ctx context.Context, r slog.Record) error {
	h.handleEntry(h.recordToEntry(ctx, r))
	return nil
}

func (h *handler) recordToEntry(ctx context.Context, r slog.Record) logging.Entry {
	return logging.Entry{
		Timestamp: r.Time,
		Severity:  levelToSeverity(r.Level),
		Payload:   recordToMap(r, h.goa.Collect()),
		Labels:    map[string]string{"module": "genkit"},
		// TODO: add a monitored resource
		// Resource:       &monitoredres.MonitoredResource{},
		// TODO: add trace information from the context.
		// Trace:        "",
		// SpanID:       "",
		// TraceSampled: false,
	}
}

func levelToSeverity(l slog.Level) logging.Severity {
	switch {
	case l < slog.LevelInfo:
		return logging.Debug
	case l == slog.LevelInfo:
		return logging.Info
	case l < slog.LevelWarn:
		return logging.Notice
	case l < slog.LevelError:
		return logging.Warning
	case l == slog.LevelError:
		return logging.Error
	case l <= slog.LevelError+4:
		return logging.Critical
	case l <= slog.LevelError+8:
		return logging.Alert
	default:
		return logging.Emergency
	}
}
func recordToMap(r slog.Record, goras []*withsupport.GroupOrAttrs) map[string]any {
	root := map[string]any{}
	root[slog.MessageKey] = r.Message

	m := root
	for i, gora := range goras {
		if gora.Group != "" {
			if i == len(goras)-1 && r.NumAttrs() == 0 {
				continue
			}
			m2 := map[string]any{}
			m[gora.Group] = m2
			m = m2
		} else {
			for _, a := range gora.Attrs {
				handleAttr(a, m)
			}
		}
	}
	r.Attrs(func(a slog.Attr) bool {
		handleAttr(a, m)
		return true
	})
	return root
}

func handleAttr(a slog.Attr, m map[string]any) {
	if a.Equal(slog.Attr{}) {
		return
	}
	v := a.Value.Resolve()
	if v.Kind() == slog.KindGroup {
		gas := v.Group()
		if len(gas) == 0 {
			return
		}
		if a.Key == "" {
			for _, ga := range gas {
				handleAttr(ga, m)
			}
		} else {
			gm := map[string]any{}
			for _, ga := range gas {
				handleAttr(ga, gm)
			}
			m[a.Key] = gm
		}
	} else {
		m[a.Key] = v.Any()
	}
}

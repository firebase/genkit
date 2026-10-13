// Copyright 2026 Google LLC
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

package exp

import (
	"context"
	"encoding/json"
	"strings"
	"time"

	"github.com/google/uuid"
)

// Router decides which box a call goes to. It returns a routing key; the box
// then asks its [Runner] to acquire the box for that key. The presets
// [Singleton], [PerRequest] and [SessionRoute] are routers too.
//
// The route sees the request about to be dispatched, so it can key off the
// payload as well as the caller's context (req.Context). The route owns any
// key mapping; the box keeps none. A route may be stateful, e.g. to look a
// session's box up in a shared store so the mapping survives restarts and
// spans instances.
type Router interface {
	Route(ctx context.Context, req *RunActionRequest) (string, error)
}

// RouteFunc adapts a function to a [Router].
//
//	box.WithRoute(box.RouteFunc(func(ctx context.Context, req *box.RunActionRequest) (string, error) {
//		if tenant, ok := req.Context["tenant"].(string); ok {
//			return tenant, nil
//		}
//		return box.SessionIDOf(req), nil
//	}))
type RouteFunc func(ctx context.Context, req *RunActionRequest) (string, error)

// Route calls f.
func (f RouteFunc) Route(ctx context.Context, req *RunActionRequest) (string, error) {
	return f(ctx, req)
}

// NeverRelease, passed to [WithIdleTimeout], keeps every box until
// [Box.Close].
const NeverRelease time.Duration = -1

// DefaultSessionIdleTimeout is the idle timeout for [SessionRoute] and for
// custom routes when [WithIdleTimeout] is not set.
const DefaultSessionIdleTimeout = 5 * time.Minute

// SingletonKey is the routing key of the one box [Singleton] routes to, and
// the key [Box.Warm] and [Box.ListActions] use when given none.
const SingletonKey = "__singleton__"

// SharedKey is the routing key [SessionRoute] uses for calls that name no
// session.
const SharedKey = "__shared__"

// presetRoute is a router that also carries a default idle timeout, used when
// the box is created without [WithIdleTimeout].
type presetRoute struct {
	route RouteFunc
	idle  time.Duration
}

func (p presetRoute) Route(ctx context.Context, req *RunActionRequest) (string, error) {
	return p.route(ctx, req)
}

var (
	// Singleton (the default) sends every call to one long-lived box that is
	// never released.
	Singleton Router = presetRoute{
		route: func(context.Context, *RunActionRequest) (string, error) { return SingletonKey, nil },
		idle:  NeverRelease,
	}

	// PerRequest gives each call a fresh box, released as soon as the call
	// returns.
	PerRequest Router = presetRoute{
		route: func(context.Context, *RunActionRequest) (string, error) { return uuid.NewString(), nil },
		idle:  0,
	}

	// SessionRoute gives each session its own box, keyed by the context's
	// "sessionId", else the session the payload names ([SessionIDOf]), else
	// one shared box ([SharedKey]). It is stateless: every instance of a
	// deployment computes the same key for the same call. It defaults to
	// [DefaultSessionIdleTimeout].
	//
	// Calls that only carry a snapshot id go to the shared box, so give the
	// boxed agent a durable session store that every box can read: routing
	// decides placement, the store decides whether a conversation survives.
	SessionRoute Router = presetRoute{
		route: func(_ context.Context, req *RunActionRequest) (string, error) {
			if id, ok := req.Context["sessionId"].(string); ok && id != "" {
				return id, nil
			}
			if id := SessionIDOf(req); id != "" {
				return id, nil
			}
			return SharedKey, nil
		},
		idle: DefaultSessionIdleTimeout,
	}
)

// defaultIdleTimeout is the idle timeout for route when none is set
// explicitly: the preset's own, else the session default.
func defaultIdleTimeout(route Router) time.Duration {
	if p, ok := route.(presetRoute); ok {
		return p.idle
	}
	return DefaultSessionIdleTimeout
}

// SessionIDOf returns the agent session a request's payload names: an agent
// turn's init.sessionId (server-managed state) or init.state.sessionId
// (client-managed state), or a snapshot read's sessionId. It returns "" for
// everything else, including calls that only carry a snapshot id and a first
// turn that lets the box mint the session id.
func SessionIDOf(req *RunActionRequest) string {
	switch {
	case strings.HasPrefix(req.Key, "/agent/"):
		var init struct {
			SessionID string `json:"sessionId"`
			State     *struct {
				SessionID string `json:"sessionId"`
			} `json:"state"`
		}
		if json.Unmarshal(req.Init, &init) != nil {
			return ""
		}
		if init.SessionID != "" {
			return init.SessionID
		}
		if init.State != nil {
			return init.State.SessionID
		}
	case strings.HasPrefix(req.Key, "/agent-snapshot/"), strings.HasPrefix(req.Key, "/agent-wait/"):
		var lookup struct {
			SessionID string `json:"sessionId"`
		}
		if json.Unmarshal(req.Input, &lookup) == nil {
			return lookup.SessionID
		}
	}
	return ""
}

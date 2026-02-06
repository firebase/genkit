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

package aix

import "errors"

// --- SessionFlowOption ---

// SessionFlowOption configures a SessionFlow.
type SessionFlowOption[State any] interface {
	applySessionFlow(*sessionFlowOptions[State]) error
}

type sessionFlowOptions[State any] struct {
	store    SnapshotStore[State]
	callback SnapshotCallback[State]
}

func (o *sessionFlowOptions[State]) applySessionFlow(opts *sessionFlowOptions[State]) error {
	if o.store != nil {
		if opts.store != nil {
			return errors.New("cannot set snapshot store more than once (WithSnapshotStore)")
		}
		opts.store = o.store
	}
	if o.callback != nil {
		if opts.callback != nil {
			return errors.New("cannot set snapshot callback more than once (WithSnapshotCallback)")
		}
		opts.callback = o.callback
	}
	return nil
}

// WithSnapshotStore sets the store for persisting snapshots.
func WithSnapshotStore[State any](store SnapshotStore[State]) SessionFlowOption[State] {
	return &sessionFlowOptions[State]{store: store}
}

// WithSnapshotCallback configures when snapshots are created.
// If not provided and a store is configured, snapshots are always created.
func WithSnapshotCallback[State any](cb SnapshotCallback[State]) SessionFlowOption[State] {
	return &sessionFlowOptions[State]{callback: cb}
}

// --- StreamBidiOption ---

// StreamBidiOption configures a StreamBidi call.
type StreamBidiOption[State any] interface {
	applyStreamBidi(*streamBidiOptions[State]) error
}

type streamBidiOptions[State any] struct {
	state      *SessionState[State]
	snapshotID string
}

func (o *streamBidiOptions[State]) applyStreamBidi(opts *streamBidiOptions[State]) error {
	if o.state != nil {
		if opts.state != nil {
			return errors.New("cannot set state more than once (WithState)")
		}
		opts.state = o.state
	}
	if o.snapshotID != "" {
		if opts.snapshotID != "" {
			return errors.New("cannot set snapshot ID more than once (WithSnapshotID)")
		}
		opts.snapshotID = o.snapshotID
	}
	return nil
}

// WithState sets the initial state for the invocation.
// Use this for client-managed state where the client sends state directly.
func WithState[State any](state *SessionState[State]) StreamBidiOption[State] {
	return &streamBidiOptions[State]{state: state}
}

// WithSnapshotID loads state from a persisted snapshot by ID.
// Use this for server-managed state where snapshots are stored.
func WithSnapshotID[State any](id string) StreamBidiOption[State] {
	return &streamBidiOptions[State]{snapshotID: id}
}

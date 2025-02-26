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
	"encoding/json"
	"errors"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/google/uuid"
	"github.com/invopop/jsonschema"
)

// Sessions are by default stored in memory only.
// Implement the SessionStore interface to persist state.
type SessionStore interface {
	Get(sessionId string) (data SessionData, err error)
	Save(sessionId string, data SessionData) error
}

type SessionData struct {
	State       map[string]any           `json:"state,omitempty"`       // Any state that should be stored
	StateSchema *jsonschema.Schema       `json:"stateschema,omitempty"` // Schema for state variables
	Threads     map[string][]*ai.Message `json:"threads,omitempty"`     // Messages by thread name
}

type Session struct {
	Genkit       *Genkit
	ID           string         // The session id
	SessionData  SessionData    // The data for the session
	DefaultState map[string]any // Default state variable values
	Store        SessionStore   // The store for the session, defaults to in-memory storage
}

type SessionOption func(s *Session) error // SessionOption configures params for the session
type sessionKey string                    // A session key

const (
	currentSessionID    sessionKey = "currentSessionID"
	currentSessionStore sessionKey = "currentSessionStore"
)

// NewSession creates a new session with the provided options.
// If no store is provided, it defaults to in-memory storage.
func NewSession(ctx context.Context, opts ...SessionOption) (session *Session, err error) {
	s := &Session{}

	for _, with := range opts {
		err := with(s)
		if err != nil {
			return nil, err
		}
	}

	if s.Store == nil {
		s.Store = &InMemorySessionStore{}
	}

	if s.ID == "" {
		s.ID = uuid.New().String()
	}

	if s.SessionData.Threads == nil {
		s.SessionData.Threads = make(map[string][]*ai.Message)
	}

	// Only update state with defaults if not already set, eg. via WithSessionData
	if s.SessionData.State == nil {
		s.SessionData.State = s.DefaultState
	}

	// Initialize session in store
	s.Store.Save(s.ID, s.SessionData)

	return s, nil
}

// LoadSession loads sessiondata from store, and returns a session.
func LoadSession(ctx context.Context, sessionId string, store SessionStore) (session *Session, err error) {
	sessionData, err := store.Get(sessionId)
	if err != nil {
		return nil, err
	}

	session = &Session{
		ID:          sessionId,
		SessionData: sessionData,
		Store:       store,
	}

	return session, nil
}

// UpdateState takes any data and sets it as state in the store.
func (s *Session) UpdateState(state any) error {
	var err error

	// Ensure sessionData is up to date
	sessionData, err := s.Store.Get(s.ID)
	if err != nil {
		return err
	}
	s.SessionData = sessionData

	s.SessionData.StateSchema, s.SessionData.State, err = getSchemaAndDefaults(state)
	if err != nil {
		return err
	}

	return s.Store.Save(s.ID, s.SessionData)
}

// UpdateMessages takes a threadName and a slice of messages.
func (s *Session) UpdateMessages(threadName string, messages []*ai.Message) error {
	// Ensure sessionData is up to date
	sessionData, err := s.Store.Get(s.ID)
	if err != nil {
		return err
	}
	s.SessionData = sessionData

	s.SessionData.Threads[threadName] = messages
	return s.Store.Save(s.ID, s.SessionData)
}

// Set current session ID in context.
func (s *Session) SetContext(ctx context.Context) context.Context {
	ctx = context.WithValue(ctx, currentSessionID, s.ID)
	ctx = context.WithValue(ctx, currentSessionStore, s.Store)

	return ctx
}

// Find current session ID in context, returns session if found.
func SessionFromContext(ctx context.Context) (session *Session, err error) {
	sessionID, ok := ctx.Value(currentSessionID).(string)
	if !ok {
		return nil, errors.New("genkit.SessionFromContext: no session ID found in context")
	}

	store, ok := ctx.Value(currentSessionStore).(SessionStore)
	if !ok {
		return nil, errors.New("genkit.SessionFromContext: no session store found in context")
	}

	session, err = LoadSession(ctx, sessionID, store)
	if err != nil {
		return nil, err
	}

	return session, nil
}

// WithSessionID sets the session id.
func WithSessionID(id string) SessionOption {
	return func(s *Session) error {
		if s.ID != "" {
			return errors.New("genkit.WithSessionID: cannot set session id more than once")
		}
		s.ID = id
		return nil
	}
}

// WithSessionData sets the session data.
func WithSessionData(data SessionData) SessionOption {
	return func(s *Session) error {
		if s.SessionData.Threads != nil {
			return errors.New("genkit.WithSessionData: cannot set session data more than once")
		}
		s.SessionData = data
		return nil
	}
}

// WithSessionStore sets a session store for the session.
func WithSessionStore(store SessionStore) SessionOption {
	return func(s *Session) error {
		if s.Store != nil {
			return errors.New("genkit.WithSessionStore: cannot set session store more than once")
		}
		s.Store = store
		return nil
	}
}

// WithStateType uses the type provided to derive the state schema.
// If passing eg. a struct with values, the struct definition will serve as the schema, the values will serve as defaults.
func WithStateType(state any) SessionOption {
	return func(s *Session) error {
		if s.SessionData.StateSchema != nil {
			return errors.New("genkit.WithStateType: cannot set state type more than once")
		}

		var err error
		s.SessionData.StateSchema, s.DefaultState, err = getSchemaAndDefaults(state)
		if err != nil {
			return err
		}

		return nil
	}
}

// Helper function to derive schema and defaults from state.
func getSchemaAndDefaults(state any) (schema *jsonschema.Schema, defaults map[string]any, err error) {
	var defaultState map[string]any

	// Handle primitives, default to "state" as key
	switch v := state.(type) {
	case int:
		defaultState = map[string]any{"state": v}
	case float32:
	case float64:
		defaultState = map[string]any{"state": v}
	case string:
		defaultState = map[string]any{"state": v}
	// Pass map directly
	case map[string]any:
		defaultState = v
	case nil:
		state = map[string]any{}
	}

	schema = base.InferJSONSchemaNonReferencing(state)

	// Handle structs
	if defaultState == nil {
		// Set values as default state
		structMap := base.SchemaAsMap(schema)
		data, err := json.Marshal(state)
		if err != nil {
			return nil, nil, err
		}

		err = json.Unmarshal(data, &structMap)
		if err != nil {
			return nil, nil, err
		}

		defaultState = structMap
	}

	return schema, defaultState, nil
}

// Default in-memory session store.
type InMemorySessionStore struct {
	Data map[string]SessionData // The session data keyed by session id
	mu   sync.RWMutex
}

func (s *InMemorySessionStore) Get(sessionId string) (data SessionData, err error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if _, ok := s.Data[sessionId]; !ok {
		return data, errors.New("genkit.InMemorySessionStore.Get: session not found")
	}
	return s.Data[sessionId], nil
}

func (s *InMemorySessionStore) Save(sessionId string, data SessionData) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.Data[sessionId]; !ok {
		s.Data = make(map[string]SessionData)
	}
	s.Data[sessionId] = data
	return nil
}

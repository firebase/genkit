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
	"errors"

	"github.com/firebase/genkit/go/ai"
	"github.com/google/uuid"
)

// Sessions are by default stored in memory only.
// Implement the SessionStore interface to persist state.
type SessionStore interface {
	Get(sessionId string) (data SessionData, err error)
	Save(sessionId string, data SessionData) error
}

type SessionData struct {
	// Any state that should be stored
	State any
	// The messages for each thread
	Threads map[string][]*ai.Message
}

type Session struct {
	// The session id
	ID string
	// The data for the session
	SessionData SessionData
	// The store for the session, defaults to in-memory storage
	Store SessionStore
}

// SessionOption configures params for the session
type SessionOption func(s *Session) error

// NewSession creates a new session with the provided options.
// If no store is provided, it defaults to in-memory storage.
func NewSession(opts ...SessionOption) (session *Session, err error) {
	s := &Session{}

	for _, with := range opts {
		err := with(s)
		if err != nil {
			return nil, err
		}
	}

	if s.Store == nil {
		s.Store = &InMemSessionStore{}
	}

	if s.ID == "" {
		s.ID = uuid.New().String()
	}

	if s.SessionData.Threads == nil {
		s.SessionData = SessionData{
			Threads: make(map[string][]*ai.Message),
		}
	}

	// Initialize session in store
	s.Store.Save(s.ID, s.SessionData)

	return s, nil
}

// LoadSession loads sessiondata from store, and returns a session.
func LoadSession(sessionId string, store SessionStore) (session *Session, err error) {
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

// TODO: Session from context? How does that work? From genkit registry when that is done?

// TODO: Is this state from the js docs?
func (s *Session) UpdateState(data any) error {
	s.SessionData.State = data
	return s.Store.Save(s.ID, s.SessionData)
}

// UpdateMessages takes a threadName and a slice of messages.
func (s *Session) UpdateMessages(threadName string, messages []*ai.Message) error {
	s.SessionData.Threads[threadName] = messages
	return s.Store.Save(s.ID, s.SessionData)
}

// WithSessionID sets the session id.
func WithSessionID(id string) SessionOption {
	return func(s *Session) error {
		if s.ID != "" {
			return errors.New("cannot set session id (WithSessionID) more than once")
		}
		s.ID = id
		return nil
	}
}

// WithSessionData sets the session data.
func WithSessionData(data SessionData) SessionOption {
	return func(s *Session) error {
		if s.SessionData.Threads != nil {
			return errors.New("cannot set session data (WithSessionData) more than once")
		}
		s.SessionData = data
		return nil
	}
}

// WithSessionStore sets a session store for the session.
func WithSessionStore(store SessionStore) SessionOption {
	return func(s *Session) error {
		if s.Store != nil {
			return errors.New("cannot set session store (WithSessionStore) more than once")
		}
		s.Store = store
		return nil
	}
}

// How is this supposed to work????
// func WithStateType() SessionOption {

// }

// Default in-memory session store.
type InMemSessionStore struct {
	SessionData map[string]SessionData
}

func (s *InMemSessionStore) Get(sessionId string) (data SessionData, err error) {
	if _, ok := s.SessionData[sessionId]; !ok {
		return data, errors.New("session not found")
	}
	return s.SessionData[sessionId], nil
}

func (s *InMemSessionStore) Save(sessionId string, data SessionData) error {
	if _, ok := s.SessionData[sessionId]; !ok {
		s.SessionData = make(map[string]SessionData)
	}
	s.SessionData[sessionId] = data
	return nil
}

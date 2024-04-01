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
	"fmt"
	"time"
)

// A contextKey is a unique, typed key for a value stored in a context.
type contextKey[T any] struct {
	key *int
}

func newContextKey[T any]() contextKey[T] {
	return contextKey[T]{key: new(int)}
}

// newContext returns ctx augmented with this key and the given value.
func (k contextKey[T]) newContext(ctx context.Context, value T) context.Context {
	return context.WithValue(ctx, k.key, value)
}

// fromContext returns the value associated with this key in the context,
// or the zero value for T if the key is not present.
func (k contextKey[T]) fromContext(ctx context.Context) T {
	t, _ := ctx.Value(k.key).(T)
	return t
}

// zero returns the zero value for T.
func zero[T any]() T {
	var z T
	return z
}

// jsonString returns json.Marshal(x) as a string. If json.Marshal returns
// an error, jsonString returns the error text as a JSON string beginning "ERROR:".
func jsonString(x any) string {
	bytes, err := json.Marshal(x)
	if err != nil {
		bytes, _ = json.Marshal(fmt.Sprintf("ERROR: %v", err))
	}
	return string(bytes)
}

// Milliseconds represents a time as the number of milliseconds since the Unix epoch.
type Milliseconds float64

func timeToMilliseconds(t time.Time) Milliseconds {
	nsec := t.UnixNano()
	return Milliseconds(float64(nsec) / 1e6)
}

func (m Milliseconds) time() time.Time {
	sec := int64(m / 1e3)
	nsec := int64((float64(m) - float64(sec*1e3)) * 1e6)
	return time.Unix(sec, nsec)
}

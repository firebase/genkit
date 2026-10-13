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
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/json"

	"github.com/firebase/genkit/go/core/status"
)

// Reflection wire contract. These mirror the genkit package's reflection
// config, which it does not export; they are protocol constants.
const (
	// reflectionEnabledEnv turns a runtime's reflection API on outside
	// GENKIT_ENV=dev. Runners always set it: the box's link to its host is not
	// the Dev UI's, so it must not depend on the caller's dev mode or opt-out.
	reflectionEnabledEnv = "GENKIT_REFLECTION_ENABLED"
	// reflectionSecretEnv is where a runtime reads its reflection secret.
	reflectionSecretEnv = "GENKIT_REFLECTION_SECRET_TOKEN"
	// reflectionV2ServerEnv points a runtime at a v2 manager to dial.
	reflectionV2ServerEnv = "GENKIT_REFLECTION_V2_SERVER"
	// runtimeIDEnv is the id a runtime registers with.
	runtimeIDEnv = "GENKIT_RUNTIME_ID"
	// reflectionSecretHeader carries the secret on v1 requests.
	reflectionSecretHeader = "x-genkit-reflection-secret"
	// reflectionAuthErrorCode is the JSON-RPC error for a refused v2
	// register; it tells the runtime not to reconnect.
	reflectionAuthErrorCode = -32001
)

// secretsEqual compares in constant time; hashing first hides the expected
// length.
func secretsEqual(a, b string) bool {
	ha, hb := sha256.Sum256([]byte(a)), sha256.Sum256([]byte(b))
	return subtle.ConstantTimeCompare(ha[:], hb[:]) == 1
}

// newSecret returns a fresh random reflection secret.
func newSecret() string {
	b := make([]byte, 32)
	_, _ = rand.Read(b) // crypto/rand.Read never fails.
	return base64.RawURLEncoding.EncodeToString(b)
}

// wireError is the error object both reflection transports report: v1 in its
// {"error": ...} envelope, v2 as a JSON-RPC error's data. Code is a canonical
// status code.
type wireError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Details struct {
		TraceID string `json:"traceId,omitempty"`
		Stack   string `json:"stack,omitempty"`
	} `json:"details"`
}

// toStatusError turns a box's error report into a [status.Error] with the
// same status, so a caller can branch on it (status.Of) across the hop. The
// message stays the box's own; the box's trace id and stack ride in Details.
func (w *wireError) toStatusError() *status.Error {
	name := status.FromCode(w.Code)
	if w.Code == 0 {
		name = status.Unknown
	}
	e := status.Errorf(status.Base(name), "%s", w.Message)
	details := map[string]any{}
	if w.Details.TraceID != "" {
		details["boxTraceId"] = w.Details.TraceID
	}
	if w.Details.Stack != "" {
		details["boxStack"] = w.Details.Stack
	}
	if len(details) > 0 {
		e.Details = details
	}
	return e
}

// decodeWireError decodes raw into a status error, or reports false when raw
// is not a reflection error object.
func decodeWireError(raw json.RawMessage) (*status.Error, bool) {
	var w wireError
	if len(raw) == 0 || json.Unmarshal(raw, &w) != nil || (w.Code == 0 && w.Message == "") {
		return nil, false
	}
	return w.toStatusError(), true
}

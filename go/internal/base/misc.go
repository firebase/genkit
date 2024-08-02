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

package base

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
)

// An Environment is the execution context in which the program is running.
type Environment string

const (
	EnvironmentDev  Environment = "dev"  // development: testing, debugging, etc.
	EnvironmentProd Environment = "prod" // production: user data, SLOs, etc.
)

// Zero returns the Zero value for T.
func Zero[T any]() T {
	var z T
	return z
}

// Clean returns a valid filename for id.
func Clean(id string) string {
	return url.PathEscape(id)
}

// HTTPError is an error that includes an HTTP status code.
type HTTPError struct {
	Code int
	Err  error
}

func (e *HTTPError) Error() string {
	return fmt.Sprintf("%s: %s", http.StatusText(e.Code), e.Err)
}

// FlowStater is the common type of all flowState[I, O] types.
type FlowStater interface {
	IsFlowState()
	ToJSON() ([]byte, error)
	CacheAt(key string) json.RawMessage
	CacheSet(key string, val json.RawMessage)
}

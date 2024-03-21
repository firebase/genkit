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

// Package genkit is the genkit API for Go.
package genkit

import (
	"context"
	"sync"
)

var initMu sync.Mutex
var initted bool

// Init should be called immediately after all calls to RegisterAction and RegisterTraceStore.
// The returned function should be called before the program ends to ensure that
// all pending data is stored.
// Init panics if called a second time.
func Init() (shutdown func(context.Context) error, err error) {
	initMu.Lock()
	defer initMu.Unlock()
	if initted {
		panic("Init called twice")
	}
	initted = true
	return initTracing()
}

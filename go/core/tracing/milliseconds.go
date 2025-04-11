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

// Package gtime provides time functionality for Go Genkit.
package tracing

import "time"

// Milliseconds represents a time as the number of milliseconds since the Unix epoch.
type Milliseconds float64

// ToMilliseconds converts a time.Time to a Milliseconds.
func ToMilliseconds(t time.Time) Milliseconds {
	nsec := t.UnixNano()
	return Milliseconds(float64(nsec) / 1e6)
}

// Time converts a Milliseconds to a time.Time.
func (m Milliseconds) Time() time.Time {
	sec := int64(m / 1e3)
	nsec := int64((float64(m) - float64(sec*1e3)) * 1e6)
	return time.Unix(sec, nsec)
}

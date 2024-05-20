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

// Package common provides common functionality for Go Genkit.
package common

import (
	"time"
)

// Milliseconds represents a time as the number of milliseconds since the Unix epoch.
type Milliseconds float64

func TimeToMilliseconds(t time.Time) Milliseconds {
	nsec := t.UnixNano()
	return Milliseconds(float64(nsec) / 1e6)
}

func (m Milliseconds) Time() time.Time {
	sec := int64(m / 1e3)
	nsec := int64((float64(m) - float64(sec*1e3)) * 1e6)
	return time.Unix(sec, nsec)
}

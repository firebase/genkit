// Copyright 2024 Google LLC
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

// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package tracing

import (
	"testing"
	"time"
)

func TestMilliseconds(t *testing.T) {
	for _, tm := range []time.Time{
		time.Unix(0, 0),
		time.Unix(1, 0),
		time.Unix(100, 554),
		time.Date(2024, time.March, 24, 1, 2, 3, 4, time.UTC),
	} {
		m := ToMilliseconds(tm)
		got := m.Time()
		// Compare to the nearest millisecond. Due to the floating-point operations in the above
		// two functions, we can't be sure that the round trip is more accurate than that.
		if !got.Round(time.Millisecond).Equal(tm.Round(time.Millisecond)) {
			t.Errorf("got %v, want %v", got, tm)
		}
	}
}

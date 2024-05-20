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

package common

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
		m := TimeToMilliseconds(tm)
		got := m.Time()
		// Compare to the nearest millisecond. Due to the floating-point operations in the above
		// two functions, we can't be sure that the round trip is more accurate than that.
		if !got.Round(time.Millisecond).Equal(tm.Round(time.Millisecond)) {
			t.Errorf("got %v, want %v", got, tm)
		}
	}
}

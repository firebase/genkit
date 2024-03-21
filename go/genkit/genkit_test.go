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
	"log"
	"os"
	"testing"
)

func TestMain(m *testing.M) {
	shutdown, err := Init()
	if err != nil {
		log.Fatal(err)
	}
	code := m.Run()
	if err := shutdown(context.Background()); err != nil {
		log.Fatal(err)
	}
	os.Exit(code)
}

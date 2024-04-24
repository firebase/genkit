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

// This program can be manually tested like so:
// Start the server listening on port 3100:
//
//	go run . &
//
// Tell it to run an action:
//
//	curl -d '{"key":"/flow/parent/parent", "input":{"start": {"input":null}}}'  http://localhost:3100/api/runAction
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/google/genkit/go/genkit"
)

func main() {
	basic := genkit.DefineFlow("basic", func(ctx context.Context, subject string, _ genkit.NoStream) (string, error) {
		foo, err := genkit.Run(ctx, "call-llm", func() (string, error) { return "subject: " + subject, nil })
		if err != nil {
			return "", err
		}
		return genkit.Run(ctx, "call-llm", func() (string, error) { return "foo: " + foo, nil })
	})

	genkit.DefineFlow("parent", func(ctx context.Context, _ struct{}, _ genkit.NoStream) (string, error) {
		return genkit.RunFlow(ctx, basic, "foo")
	})

	type chunk struct {
		Count int `json:"count"`
	}

	genkit.DefineFlow("streamy", func(ctx context.Context, count int, cb genkit.StreamingCallback[chunk]) (string, error) {
		i := 0
		if cb != nil {
			for ; i < count; i++ {
				if err := cb(ctx, chunk{i}); err != nil {
					return "", err
				}
			}
		}
		return fmt.Sprintf("done: %d, streamed: %d times", count, i), nil
	})

	if err := genkit.StartDevServer(""); err != nil {
		log.Fatal(err)
	}
}

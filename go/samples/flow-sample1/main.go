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
// Tell it to run a flow:
//
//	curl -d '{"key":"/flow/parent/parent", "input":{"start": {"input":null}}}' http://localhost:3100/api/runAction
//
// In production mode (GENKIT_ENV missing or set to "prod"):
// Start the server listening on port 3400:
//
//	go run . &
//
// Tell it to run a flow:
//
// curl -d '{}' http://localhost:3400/parent

package main

import (
	"context"
	"fmt"
	"log"
	"strconv"

	"github.com/firebase/genkit/go/genkit"
)

func main() {
	basic := genkit.DefineFlow("basic", func(ctx context.Context, subject string) (string, error) {
		foo, err := genkit.Run(ctx, "call-llm", func() (string, error) { return "subject: " + subject, nil })
		if err != nil {
			return "", err
		}
		return genkit.Run(ctx, "call-llm", func() (string, error) { return "foo: " + foo, nil })
	})

	genkit.DefineFlow("parent", func(ctx context.Context, _ struct{}) (string, error) {
		return basic.Run(ctx, "foo")
	})

	type complex struct {
		Key   string `json:"key"`
		Value int    `json:"value"`
	}

	genkit.DefineFlow("complex", func(ctx context.Context, c complex) (string, error) {
		foo, err := genkit.Run(ctx, "call-llm", func() (string, error) { return c.Key + ": " + strconv.Itoa(c.Value), nil })
		if err != nil {
			return "", err
		}
		return foo, nil
	})

	type chunk struct {
		Count int `json:"count"`
	}

	genkit.DefineStreamingFlow("streamy", func(ctx context.Context, count int, cb func(context.Context, chunk) error) (string, error) {
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

	if err := genkit.Init(context.Background(), nil); err != nil {
		log.Fatal(err)
	}
}

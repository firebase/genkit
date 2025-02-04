// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/vertexai"
)

func main() {
	ctx := context.Background()
	if err := vertexai.Init(ctx, nil); err != nil {
		log.Fatal(err)
	}
	m := vertexai.Model("gemini-1.5-flash-002")
	if m == nil {
		log.Fatal(errors.New("vertexai init failed"))
	}
	resp, err := ai.Generate(ctx, m,
		ai.WithConfig(&ai.GenerationCommonConfig{Temperature: 1, TTL: time.Hour}),
		ai.WithTextPrompt("Tell me a joke about golang developers"))

	if err != nil {
		fmt.Println(err)
	}
	fmt.Println("output:", resp.Message.Text())
}

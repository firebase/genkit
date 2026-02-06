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

// This sample demonstrates the SessionFlow API for multi-turn conversation
// with token-level streaming. It runs a CLI REPL where conversation history
// is managed automatically by the session.
package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/firebase/genkit/go/ai"
	aix "github.com/firebase/genkit/go/ai/x"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/googlegenai"
	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	store := aix.NewInMemorySnapshotStore[struct{}]()

	chatFlow := genkit.DefineSessionFlow(g, "chat",
		func(ctx context.Context, resp aix.Responder[any], params *aix.SessionFlowParams[struct{}]) error {
			sess := params.Session
			return sess.Run(ctx, func(ctx context.Context, input *aix.SessionFlowInput) error {
				for chunk, err := range genkit.GenerateStream(ctx, g,
					ai.WithModel(googlegenai.ModelRef("googleai/gemini-3-flash-preview", &genai.GenerateContentConfig{
						ThinkingConfig: &genai.ThinkingConfig{
							ThinkingBudget: genai.Ptr[int32](0),
						},
					})),
					ai.WithSystem("You are a helpful assistant. Keep responses concise."),
					ai.WithMessages(sess.Messages()...),
				) {
					if err != nil {
						return err
					}
					if chunk.Done {
						sess.AddMessages(chunk.Response.Message)
						break
					}
					resp.SendChunk(chunk.Chunk)
				}

				return nil
			})
		},
		aix.WithSnapshotStore(store),
		aix.WithSnapshotCallback(aix.SnapshotOn[struct{}](aix.TurnEnd)),
	)

	fmt.Println("Session Flow Chat (type 'quit' to exit)")
	fmt.Println()

	conn, err := chatFlow.StreamBidi(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	reader := bufio.NewReader(os.Stdin)
	for {
		fmt.Print("> ")
		input, _ := reader.ReadString('\n')
		input = strings.TrimSpace(input)

		if input == "quit" || input == "exit" {
			break
		}
		if input == "" {
			continue
		}

		if err := conn.SendText(input); err != nil {
			fmt.Fprintf(os.Stderr, "Send error: %v\n", err)
			break
		}

		fmt.Println()

		for chunk, err := range conn.Receive() {
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error: %v\n", err)
				break
			}
			if chunk.Chunk != nil {
				fmt.Print(chunk.Chunk.Text())
			}
			if chunk.SnapshotCreated != "" {
				fmt.Printf("\n[snapshot: %s]", chunk.SnapshotCreated)
			}
			if chunk.EndTurn {
				fmt.Println()
				fmt.Println()
				break
			}
		}
	}

	conn.Close()
}

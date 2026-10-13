// Copyright 2026 Google LLC
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

// Command boxed is the boxed side of the box-agent sample: the WHOLE agent
// (model calls, tools, conversation state) lives here, started by the parent
// program, one process per chat session. Nothing but reflection calls cross
// the boundary.
package main

import (
	"context"
	"os"

	"github.com/firebase/genkit/go/ai"
	aix "github.com/firebase/genkit/go/ai/exp"
	"github.com/firebase/genkit/go/ai/exp/localstore"
	"github.com/firebase/genkit/go/core/status"
	"github.com/firebase/genkit/go/genkit"
	genkitx "github.com/firebase/genkit/go/genkit/exp"
	box "github.com/firebase/genkit/go/plugins/box/exp"
	"github.com/firebase/genkit/go/plugins/googlegenai"
)

// NotesState is the agent's custom session state. The host declares the same
// schema so the Dev UI can render it.
type NotesState struct {
	Notes []string `json:"notes,omitempty"`
}

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}), genkit.WithExperimental())

	takeNote := genkit.DefineTool(g, "takeNote",
		"Remember a short note for later in this conversation.",
		func(ctx *ai.ToolContext, in struct {
			Note string `json:"note"`
		}) (struct {
			PID   int `json:"pid"`
			Count int `json:"count"`
		}, error) {
			var out struct {
				PID   int `json:"pid"`
				Count int `json:"count"`
			}
			sess := aix.SessionFromContext[NotesState](ctx)
			if sess == nil {
				return out, status.Errorf(status.ErrFailedPrecondition, "takeNote must be called inside a session")
			}
			sess.UpdateCustom(func(s NotesState) NotesState {
				s.Notes = append(s.Notes, in.Note)
				out.Count = len(s.Notes)
				return s
			})
			// The pid shows each session gets its own box process.
			out.PID = os.Getpid()
			return out, nil
		})

	// Shared by every box process, so any box can resume any session: a box
	// released after idling (or a call routed elsewhere) loses nothing. With
	// an in-memory store the conversation would die with its box.
	store, err := localstore.NewFileSessionStore[NotesState](".genkit/box-sessions")
	if err != nil {
		panic(err)
	}
	genkitx.DefineAgent(g, "notesAgent",
		aix.InlinePrompt{
			ai.WithModelName("googleai/gemini-flash-latest"),
			ai.WithSystem("You are a note taker. When the user shares something worth remembering, call takeNote. Keep answers short, and mention the pid takeNote returns."),
			ai.WithTools(takeNote),
		},
		aix.WithSessionStore(store),
	)

	// Serve until the runner stops this box.
	box.ServeIfRuntime(ctx)
}

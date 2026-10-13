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
//
// SPDX-License-Identifier: Apache-2.0

// Package exp is Genkit in a Box: it runs Genkit actions (tools, flows,
// agents) somewhere other than the current process and calls them as if they
// were local. "Somewhere" can be a subprocess, a local OS sandbox, a container
// or a remote runtime; you swap a [Runner], not your code.
//
// Two reasons to box: isolation (an LLM drives a shell tool you don't fully
// trust; box the tool, keep the agent and model keys outside) and relocation
// (run an action in another process, language or machine behind the same call
// site).
//
// A box hands out proxies: real Genkit actions that forward each call to the
// box, so they compose anywhere a local action does.
//
//	b := box.New(g, runner)
//	defer b.Close(ctx)
//
//	// Same language: hand over the real tool, no schema restatement.
//	boxedRunShell := box.NewToolFrom(b, runShell)
//	// No local copy: declare the shape.
//	search := box.NewTool[SearchIn, SearchOut](b, "search", "Search the repo.")
//
//	genkit.Generate(ctx, g, ai.WithTools(boxedRunShell, search), ...)
//
// NewX proxies are unregistered; the DefineX variants also register them for
// the Dev UI, and DefineXFrom must be renamed since the original occupies its
// name.
//
// [WithRoute] decides which box a call goes to ([Singleton], [PerRequest],
// [SessionRoute], or your own [Router]); [WithIdleTimeout] decides how long an
// idle box lives.
//
// This package is experimental and may change in any minor release.
package exp

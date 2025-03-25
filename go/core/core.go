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
//
// SPDX-License-Identifier: Apache-2.0

// Run the npm script that generates JSON Schemas from the zod types
// in the *.ts files. It writes the result to genkit-tools/genkit-schema.json
//go:generate npm --prefix ../../genkit-tools run export:schemas

// Run the Go code generator on the file just created.
//go:generate go run ../internal/cmd/jsonschemagen -outdir .. -config schemas.config ../../genkit-tools/genkit-schema.json ai

// Package core implements Genkit actions and other essential machinery.
// This package is primarily intended for Genkit internals and for plugins.
// Genkit applications should use the genkit package.
package core

import (
	"github.com/firebase/genkit/go/internal/registry"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// RegisterSpanProcessor registers an OpenTelemetry SpanProcessor for tracing.
func RegisterSpanProcessor(r *registry.Registry, sp sdktrace.SpanProcessor) {
	r.RegisterSpanProcessor(sp)
}

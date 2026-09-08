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

package base

import (
	"encoding/json"
	"fmt"
)

// ToolInterruptError is the error a tool call returns to pause generation and
// hand control back to the caller. ai/tool.Interrupt is the one public way to
// raise it; ai recognizes it with errors.As when the tool returns, records Data
// on the interrupted tool request part, and reports it through
// ai.IsToolInterruptError. The type is internal so that raising an interrupt
// has a single entry point and the in-process representation can change with
// the wire contract.
//
// Data is the interrupt payload: nil for a bare interrupt, otherwise a struct
// or a map that serializes to a JSON object. ai validates the shape when the
// tool returns.
type ToolInterruptError struct {
	Data any
}

func (e *ToolInterruptError) Error() string {
	if e.Data != nil {
		if data, err := json.MarshalIndent(e.Data, "", "  "); err == nil {
			return fmt.Sprintf("tool execution interrupted: \n\n%s", string(data))
		}
	}
	return "tool execution interrupted"
}

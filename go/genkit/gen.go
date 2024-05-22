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

// This file was generated by jsonschemagen. DO NOT EDIT.

package genkit

import "github.com/firebase/genkit/go/gtime"

type flowError struct {
	Error      string `json:"error,omitempty"`
	Stacktrace string `json:"stacktrace,omitempty"`
}

type flowExecution struct {
	// end time in milliseconds since the epoch
	EndTime gtime.Milliseconds `json:"endTime,omitempty"`
	// start time in milliseconds since the epoch
	StartTime gtime.Milliseconds `json:"startTime,omitempty"`
	TraceIDs  []string           `json:"traceIds,omitempty"`
}

// blockedOnStep describes the step of the flow that the flow is blocked on.
type blockedOnStep struct {
	Name   string `json:"name,omitempty"`
	Schema string `json:"schema,omitempty"`
}

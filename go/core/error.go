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

// Package core provides base error types and utilities for Genkit.
package core

import (
	"fmt"
	"runtime/debug"
)

type GenkitReflectionAPIDetailsWireFormat struct {
	Stack   *string `json:"stack,omitempty"` // Use pointer for optional
	TraceID *string `json:"traceId,omitempty"`
}

// GenkitReflectionAPIErrorWireFormat is the wire format for HTTP errors.
type GenkitReflectionAPIErrorWireFormat struct {
	Details *GenkitReflectionAPIDetailsWireFormat `json:"details,omitempty"` // Pointer to allow nil details
	Message string                                `json:"message"`
	Code    int                                   `json:"code"` // Defaults handled in creation logic
}

// HTTPErrorWireFormat is the wire format for HTTP error details for callables.
type HTTPErrorWireFormat struct {
	Details any        `json:"details,omitempty"` // Use 'any' (interface{}) for arbitrary details
	Message string     `json:"message"`
	Status  StatusName `json:"status"` // Use the defined StatusName type
}

// GenkitError is the base error type for Genkit errors.
type GenkitError struct {
	Message  string         `json:"message"` // Exclude from default JSON if embedded elsewhere
	Status   StatusName     `json:"status"`
	HTTPCode int            `json:"-"`                // Exclude from default JSON
	Details  map[string]any `json:"details"`          // Use map for arbitrary details
	Source   *string        `json:"source,omitempty"` // Pointer for optional
}

// Error implements the standard error interface.
func (e *GenkitError) Error() string {
	sourcePrefix := ""
	if e.Source != nil && *e.Source != "" {
		sourcePrefix = fmt.Sprintf("%s: ", *e.Source)
	}
	baseMsg := fmt.Sprintf("%s%s: %s", sourcePrefix, e.Status, e.Message)

	return baseMsg
}

// ToCallableSerializable returns a JSON-serializable representation for callable responses.
func (e *GenkitError) ToCallableSerializable() HTTPErrorWireFormat {
	msg := e.Message
	return HTTPErrorWireFormat{
		Details: e.Details,
		Status:  e.Status,
		Message: msg,
	}
}

// UserFacingError  error allows a web framework handler to know it
// is safe to return the message in a request. Other kinds of errors will
// result in a generic 500 message to avoid the possibility of internal
// exceptions being leaked to attackers.
func UserFacingError(status StatusName, message string, details map[string]any) *GenkitError {
	return &GenkitError{
		Status:  status,
		Details: details,
		Message: message,
	}
}

// ToSerializable returns a JSON-serializable representation for reflection API responses.
func (e *GenkitError) ToSerializable() GenkitReflectionAPIErrorWireFormat {
	msg := e.Message
	detailsWire := &GenkitReflectionAPIDetailsWireFormat{}
	// Populate detailsWire from e.Details map
	if stackVal, ok := e.Details["stack"].(string); ok {
		detailsWire.Stack = &stackVal
	}
	// Use TraceID field directly if set, otherwise check details map
	if traceVal, ok := e.Details["traceId"].(string); ok {
		traceIDStr := traceVal // Create a new variable to take its address
		detailsWire.TraceID = &traceIDStr
	}

	return GenkitReflectionAPIErrorWireFormat{
		Details: detailsWire,
		Code:    HTTPStatusCode(e.Status), // Use the integer code
		Message: msg,
	}
}

// GetReflectionJSON gets the JSON representation for reflection API Error responses.
func GetReflectionJSON(err error) GenkitReflectionAPIErrorWireFormat {
	if ge, ok := err.(*GenkitError); ok {
		return ge.ToSerializable()
	}
	// Handle non-Genkit errors
	stack := getErrorStack(err)
	detailsWire := &GenkitReflectionAPIDetailsWireFormat{}
	if stack != "" {
		detailsWire.Stack = &stack
	}
	return GenkitReflectionAPIErrorWireFormat{
		Message: err.Error(),                // Use the standard error message
		Code:    StatusNameToCode[INTERNAL], // Default to INTERNAL code
		Details: detailsWire,
	}
}

// getErrorStack extracts stack trace from an error object.
// This captures the stack trace of the current goroutine when called.
func getErrorStack(err error) string {
	if err == nil {
		return ""
	}
	return string(debug.Stack())
}

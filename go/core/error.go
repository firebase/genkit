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
package core // Or maybe errors? Choose your package name

import (
	"errors"
	"fmt"
	"runtime/debug"
)

type GenkitReflectionAPIDetailsWireFormat struct {
	Stack   *string `json:"stack,omitempty"` // Use pointer for optional
	TraceID *string `json:"traceId,omitempty"`
	// Use map[string]any if you need truly arbitrary fields, or embed if known.
	// For simplicity here, we only define known fields. Add more needed.
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

// --- GenkitErrorStruct ---

// GenkitErrorStruct is the base error type for Genkit errors.
type GenkitErrorStruct struct {
	OriginalMessage string         `json:"-"` // Exclude from default JSON if embedded elsewhere
	Status          StatusName     `json:"status"`
	HTTPCode        int            `json:"-"`                 // Exclude from default JSON
	Details         map[string]any `json:"details"`           // Use map for arbitrary details
	Source          *string        `json:"source,omitempty"`  // Pointer for optional
	TraceID         *string        `json:"traceId,omitempty"` // Pointer for optional
	Cause           error          `json:"-"`                 // The underlying wrapped error
}

// NewGenkitError creates a new GenkitErrorStruct.
func NewGenkitError(msg string, statusName StatusName, cause error, details map[string]any, traceID *string, source *string) *GenkitErrorStruct {
	ge := &GenkitErrorStruct{
		OriginalMessage: msg,
		Status:          statusName,
		Source:          source,
		TraceID:         traceID,
		Cause:           cause, // Store the original cause
		Details:         details,
	}

	// Inherit status from cause if it's a GenkitErrorStruct and status wasn't provided
	if ge.Status == "" { // Assuming empty string means not provided
		var causeGe *GenkitErrorStruct
		if errors.As(cause, &causeGe) { // Check if cause is GenkitErrorStruct
			ge.Status = causeGe.Status
		}
	}

	// Default status if still not set
	if ge.Status == "" {
		ge.Status = INTERNAL
	}

	// Calculate HTTP code
	ge.HTTPCode = HTTPStatusCode(ge.Status)

	// Initialize details map if nil
	if ge.Details == nil {
		ge.Details = make(map[string]any)
	}

	// Add stack trace to details if not already present
	if _, exists := ge.Details["stack"]; !exists {
		// Capture stack trace at the point of error creation
		stack := getErrorStack(ge) // Pass the error itself
		if stack != "" {
			ge.Details["stack"] = stack
		}
	}

	// Add trace_id to details if not already present and provided
	if _, exists := ge.Details["trace_id"]; !exists && traceID != nil {
		ge.Details["trace_id"] = *traceID
	}
	return ge
}

// Error implements the standard error interface.
func (e *GenkitErrorStruct) Error() string {
	sourcePrefix := ""
	if e.Source != nil && *e.Source != "" {
		sourcePrefix = fmt.Sprintf("%s: ", *e.Source)
	}
	fmt.Printf("%v", sourcePrefix)
	baseMsg := fmt.Sprintf("%s%s: %s", sourcePrefix, e.Status, e.OriginalMessage)

	// Include cause if it exists, using standard wrapping format
	if e.Cause != nil {
		return fmt.Sprintf("%s: %s", baseMsg, e.Cause.Error())
	}
	return baseMsg
}

// Unwrap provides compatibility with errors.Is and errors.As by returning the wrapped error.
func (e *GenkitErrorStruct) Unwrap() error {
	return e.Cause
}

// ToCallableSerializable returns a JSON-serializable representation for callable responses.
func (e *GenkitErrorStruct) ToCallableSerializable() HTTPErrorWireFormat {
	msg := e.OriginalMessage
	if e.Cause != nil {
		msg = e.Cause.Error() // Similar to repr(cause) - gets the error string
	}
	return HTTPErrorWireFormat{
		Details: e.Details,
		Status:  e.Status, // Directly use the status name
		Message: msg,
	}
}

// ToSerializable returns a JSON-serializable representation for reflection API responses.
func (e *GenkitErrorStruct) ToSerializable() GenkitReflectionAPIErrorWireFormat {
	msg := e.OriginalMessage
	if e.Cause != nil {
		msg = e.Cause.Error()
	}

	detailsWire := &GenkitReflectionAPIDetailsWireFormat{}
	// Populate detailsWire from e.Details map
	if stackVal, ok := e.Details["stack"].(string); ok {
		detailsWire.Stack = &stackVal
	}
	// Use TraceID field directly if set, otherwise check details map
	if e.TraceID != nil {
		detailsWire.TraceID = e.TraceID
	} else if traceVal, ok := e.Details["trace_id"].(string); ok {
		traceIDStr := traceVal // Create a new variable to take its address
		detailsWire.TraceID = &traceIDStr
	}

	return GenkitReflectionAPIErrorWireFormat{
		Details: detailsWire,
		Code:    StatusNameToCode[e.Status], // Use the integer code
		Message: msg,
	}
}

// --- Specific Error Types (as factory functions) ---

//// NewUnstableAPIError creates an error for using unstable APIs.
//func NewUnstableAPIError(level string, message *string) *GenkitErrorStruct {
//	msgPrefix := ""
//	if message != nil && *message != "" {
//		msgPrefix = fmt.Sprintf("%s ", *message)
//	}
//	errMsg := fmt.Sprintf(
//		"%sThis API requires '%s' stability level.\n\nTo use this feature, initialize Genkit using `import \"genkit/%s\"`.", // Adjusted import path for Go style
//		msgPrefix,
//		level,
//		level, // Assuming package name matches level e.g., genkit/beta
//	)
//	// Note: No cause, details, traceID, source passed here, matching Python version
//	return NewGenkitError(errMsg, FAILED_PRECONDITION, nil, nil, nil, nil)
//}

// NewUserFacingError creates an error suitable for returning to users.
func NewUserFacingError(statusName StatusName, message string, details map[string]any) *GenkitErrorStruct {
	// Note: No cause, traceID, source passed here
	return NewGenkitError(message, statusName, nil, details, nil, nil)
}

// --- Utility Functions ---

//// GetHTTPStatus gets the HTTP status code for an error.
//func GetHTTPStatus(err error) int {
//	var ge *GenkitErrorStruct
//	if errors.As(err, &ge) { // Check if the error (or any error in its chain) is a GenkitErrorStruct
//		return ge.HTTPCode
//	}
//	return 500 // Default for non-Genkit errors or nil
//}

// GetReflectionJSON gets the JSON representation for reflection API Error responses.
func GetReflectionJSON(err error) GenkitReflectionAPIErrorWireFormat {
	//fmt.Printf("%v", err)
	if ge, ok := err.(*GenkitErrorStruct); ok {
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

//
//// GetCallableJSON gets the JSON representation for callable responses.
//func GetCallableJSON(err error) HTTPErrorWireFormat {
//	var ge *GenkitErrorStruct
//	if errors.As(err, &ge) {
//		return ge.ToCallableSerializable()
//	}
//
//	// Handle non-Genkit errors
//	details := make(map[string]any)
//	stack := getErrorStack(err)
//	if stack != "" {
//		details["stack"] = stack
//	}
//
//	return HTTPErrorWireFormat{
//		Message: err.Error(), // Use the standard error message
//		Status:  INTERNAL,    // Default to INTERNAL status name
//		Details: details,     // Include stack if available
//	}
//}

//// GetErrorMessage extracts the error message string from any error.
//func GetErrorMessage(err error) string {
//	if err == nil {
//		return ""
//	}
//	return err.Error() // The standard Error() method provides this
//}

// getErrorStack extracts stack trace from an error object.
// This version captures the stack trace of the current goroutine when called.
// It doesn't rely on the error object itself containing the stack, unless
// the error object *is* specifically designed to capture and store it (like we do in NewGenkitErrorStruct).
func getErrorStack(err error) string {
	if err == nil {
		return ""
	}
	// Capture the stack trace of the current goroutine.
	// Set 'all' false to capture only the current goroutine.
	// Note: This reflects the stack *now*, not necessarily the error's origin point,
	// unless called immediately at the error site or if stored during creation.
	return string(debug.Stack())
}

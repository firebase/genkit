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

type ReflectionErrorDetails struct {
	Stack   *string `json:"stack,omitempty"` // Use pointer for optional
	TraceID *string `json:"traceId,omitempty"`
}

// ReflectionError is the wire format for HTTP errors for Reflection API responses.
type ReflectionError struct {
	Details *ReflectionErrorDetails `json:"details,omitempty"`
	Message string                  `json:"message"`
	Code    int                     `json:"code"`
}

// GenkitError is the base error type for Genkit errors.
type GenkitError struct {
	Message  string         `json:"message"` // Exclude from default JSON if embedded elsewhere
	Status   StatusName     `json:"status"`
	HTTPCode int            `json:"-"`                // Exclude from default JSON
	Details  map[string]any `json:"details"`          // Use map for arbitrary details
	Source   *string        `json:"source,omitempty"` // Pointer for optional
}

// UserFacingError is the base error type for user facing errors.
type UserFacingError struct {
	Message string         `json:"message"` // Exclude from default JSON if embedded elsewhere
	Status  StatusName     `json:"status"`
	Details map[string]any `json:"details"` // Use map for arbitrary details
}

// NewPublicError allows a web framework handler to know it
// is safe to return the message in a request. Other kinds of errors will
// result in a generic 500 message to avoid the possibility of internal
// exceptions being leaked to attackers.
func NewPublicError(status StatusName, message string, details map[string]any) *UserFacingError {
	return &UserFacingError{
		Status:  status,
		Details: details,
		Message: message,
	}
}

// Error implements the standard error interface for UserFacingError.
func (e *UserFacingError) Error() string {
	return fmt.Sprintf("%s: %s", e.Status, e.Message)
}

// NewError creates a new GenkitError with a stack trace.
func NewError(status StatusName, message string, args ...any) *GenkitError {
	// Prevents a compile-time warning about non-constant message.
	msg := message

	ge := &GenkitError{
		Status:  status,
		Message: fmt.Sprintf(msg, args...),
	}

	errStack := string(debug.Stack())
	if errStack != "" {
		ge.Details = make(map[string]any)
		ge.Details["stack"] = errStack
	}
	return ge
}

// Error implements the standard error interface.
func (e *GenkitError) Error() string {
	return e.Message
}

// ToReflectionError returns a JSON-serializable representation for reflection API responses.
func (e *GenkitError) ToReflectionError() ReflectionError {
	errDetails := &ReflectionErrorDetails{}
	if stackVal, ok := e.Details["stack"].(string); ok {
		errDetails.Stack = &stackVal
	}
	if traceVal, ok := e.Details["traceId"].(string); ok {
		errDetails.TraceID = &traceVal
	}
	return ReflectionError{
		Details: errDetails,
		Code:    HTTPStatusCode(e.Status),
		Message: e.Message,
	}
}

// ToReflectionError gets the JSON representation for reflection API Error responses.
func ToReflectionError(err error) ReflectionError {
	if ge, ok := err.(*GenkitError); ok {
		return ge.ToReflectionError()
	}

	return ReflectionError{
		Message: err.Error(),
		Code:    HTTPStatusCode(INTERNAL),
		Details: &ReflectionErrorDetails{},
	}
}

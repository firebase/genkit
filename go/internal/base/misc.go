// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package base

import (
	"fmt"
	"net/http"
	"net/url"
)

// An Environment is the execution context in which the program is running.
type Environment string

const (
	EnvironmentDev  Environment = "dev"  // development: testing, debugging, etc.
	EnvironmentProd Environment = "prod" // production: user data, SLOs, etc.
)

// Zero returns the Zero value for T.
func Zero[T any]() T {
	var z T
	return z
}

// Clean returns a valid filename for id.
func Clean(id string) string {
	return url.PathEscape(id)
}

// HTTPError is an error that includes an HTTP status code.
type HTTPError struct {
	Code int
	Err  error
}

func (e *HTTPError) Error() string {
	return fmt.Sprintf("%s: %s", http.StatusText(e.Code), e.Err)
}

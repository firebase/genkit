// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package test_utils

import (
	"slices"

	"github.com/google/go-cmp/cmp"
)

// IgnoreNoisyParts is a go-cmp/cmp package Option that allows specifying paths to ignore
// in the comparison.
func IgnoreNoisyParts(ignoredPaths []string) cmp.Option {
	return cmp.FilterPath(func(ps cmp.Path) bool {
		path := ""
		for _, p := range ps {
			if p.String() != "*" {
				path += p.String()
			}
		}

		return slices.Contains(ignoredPaths, path)
	}, cmp.Ignore())
}

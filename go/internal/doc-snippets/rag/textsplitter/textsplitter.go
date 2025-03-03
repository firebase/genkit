// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package textsplitter

type Splitter struct{}

func (Splitter) SplitText(t string) ([]string, error) {
	panic("Stub.")
}

func NewRecursiveCharacter(args ...any) Splitter {
	panic("Stub.")
}

func WithChunkSize(n int) any {
	panic("Stub.")
}

func WithChunkOverlap(n int) any {
	panic("Stub.")
}

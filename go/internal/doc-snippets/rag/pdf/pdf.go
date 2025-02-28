// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package pdf

import (
	"io"
	"os"
)

type Reader struct{}

func (Reader) GetPlainText() (io.Reader, error) {
	panic("Stub.")
}

func Open(file string) (*os.File, *Reader, error) {
	panic("Stub.")
}

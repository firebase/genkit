// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Package uri extracts the content-type and data from a media part.
// This is used by the googleai and vertexai plugins.
package uri

import (
	"encoding/base64"
	"errors"
	"strings"

	"github.com/firebase/genkit/go/ai"
)

// Data returns the content type and bytes of the media part.
func Data(p *ai.Part) (string, []byte, error) {
	if !p.IsMedia() {
		return "", nil, errors.New("not a media part")
	}

	uri := p.Text
	if strings.HasPrefix(uri, "gs://") {
		if p.ContentType == "" {
			return "", nil, errors.New("must supply contentType when using media from gs:// URLs")
		}
		return p.ContentType, []byte(uri), nil
	}

	if contents, isData := strings.CutPrefix(uri, "data:"); isData {
		prefix, data, found := strings.Cut(contents, ",")
		if !found {
			return "", nil, errors.New("failed to parse data URI: missing comma")
		}

		var dataBytes []byte
		if p, isBase64 := strings.CutSuffix(prefix, ";base64"); isBase64 {
			prefix = p
			var err error
			dataBytes, err = base64.StdEncoding.DecodeString(data)
			if err != nil {
				return "", nil, err
			}
		} else {
			dataBytes = []byte(data)
		}

		contentType := p.ContentType
		if contentType == "" {
			contentType = prefix
		}

		return contentType, dataBytes, nil
	}

	return "", nil, errors.New("could not convert media part to genai part: missing file data")
}

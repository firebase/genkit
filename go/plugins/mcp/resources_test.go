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

package mcp

import (
	"encoding/base64"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestToGenkitParts(t *testing.T) {
	client := &GenkitMCPClient{}

	t.Run("text part", func(t *testing.T) {
		contents := []*mcp.ResourceContents{
			{
				Text:     "hello world",
				MIMEType: "text/plain",
			},
		}

		parts := client.toGenkitParts(contents)
		if got := len(parts); got != 1 {
			t.Fatalf("len(parts) got = %d, want 1", got)
		}

		if got := parts[0].Text; got != "hello world" {
			t.Errorf("parts[0].Text got = %q, want %q", got, "hello world")
		}

		if got := parts[0].Kind; got != ai.PartText {
			t.Errorf("parts[0].Kind got = %v, want %v (PartText)", got, ai.PartText)
		}
	})

	t.Run("json data part", func(t *testing.T) {
		jsonData := `{"id": 123, "status": "ok"}`
		contents := []*mcp.ResourceContents{
			{
				Text:     jsonData,
				MIMEType: "application/json",
			},
		}

		parts := client.toGenkitParts(contents)
		if got := len(parts); got != 1 {
			t.Fatalf("len(parts) got = %d, want 1", got)
		}

		// In resources_mcp.go, application/json becomes a DataPart
		if got := parts[0].Kind; got != ai.PartData {
			t.Errorf("parts[0].Kind got = %v, want %v (PartData)", got, ai.PartData)
		}

		if got := parts[0].Text; got != jsonData {
			t.Errorf("parts[0].Text got = %q, want %q", got, jsonData)
		}
	})

	t.Run("binary blob part", func(t *testing.T) {
		blobData := []byte{0x00, 0x01, 0x02, 0x03}
		contents := []*mcp.ResourceContents{
			{
				Blob:     blobData,
				MIMEType: "image/png",
			},
		}

		parts := client.toGenkitParts(contents)
		if got := len(parts); got != 1 {
			t.Fatalf("len(parts) got = %d, want 1", got)
		}

		if got := parts[0].Kind; got != ai.PartMedia {
			t.Errorf("parts[0].Kind got = %v, want %v (PartMedia)", got, ai.PartMedia)
		}

		if got := parts[0].ContentType; got != "image/png" {
			t.Errorf("parts[0].ContentType got = %q, want %q", got, "image/png")
		}

		wantBase64 := base64.StdEncoding.EncodeToString(blobData)
		if got := parts[0].Text; got != wantBase64 {
			t.Errorf("parts[0].Text got = %q, want %q (base64 encoded)", got, wantBase64)
		}
	})
}

func TestToGenkitResource(t *testing.T) {
	client := &GenkitMCPClient{
		options: MCPClientOptions{Name: "srv"},
	}

	mcpRes := &mcp.Resource{
		Name:        "logs",
		URI:         "file:///var/log/app.log",
		Description: "Application logs",
		Annotations: &mcp.Annotations{
			Priority: 0.8,
		},
	}

	res := client.toGenkitResource(mcpRes)

	wantName := "srv_logs"
	if got := res.Name(); got != wantName {
		t.Errorf("res.Name() got = %q, want %q", got, wantName)
	}

	// We can't easily check URI/Description without exposing internal fields of ai.Resource implementation
	// But we can check that it doesn't crash and returns a valid object.
}

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
	"net/http"
	"testing"
)

func TestWrapHTTPClient(t *testing.T) {
	t.Run("nil headers returns client as is", func(t *testing.T) {
		original := &http.Client{}
		got := wrapHTTPClient(original, nil)
		if got != original {
			t.Errorf("wrapHTTPClient(nil headers) got different pointer, want same")
		}
	})

	t.Run("nil client returns default with timeout", func(t *testing.T) {
		got := wrapHTTPClient(nil, map[string]string{"X-Test": "Value"})
		if got == nil {
			t.Fatal("wrapHTTPClient(nil client) returned nil")
		}
		if got.Transport == nil {
			t.Fatal("transport is nil, want headerTransport")
		}
		
		_, ok := got.Transport.(*headerTransport)
		if !ok {
			t.Errorf("transport type got = %T, want *headerTransport", got.Transport)
		}
	})
}

func TestMCPClientDefaults(t *testing.T) {
	// Mock connection to avoid real network call in NewGenkitMCPClient
	// We only test the option processing here.
	opts := MCPClientOptions{
		Name: "my-mcp",
	}
	
	// We can't call NewGenkitMCPClient because it calls connect()
	// Let's test the naming in Name()
	c := &GenkitMCPClient{options: opts}
	if got := c.Name(); got != "my-mcp" {
		t.Errorf("c.Name() got = %q, want %q", got, "my-mcp")
	}
}

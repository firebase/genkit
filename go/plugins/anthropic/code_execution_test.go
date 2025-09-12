// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/firebase/genkit/go/ai"
)

func TestCodeExecutionParsing(t *testing.T) {
	// Test executable code part creation
	t.Run("CreateExecutableCodePart", func(t *testing.T) {
		// Create a mock server_tool_use part for bash execution
		bashInput := map[string]any{
			"command": "python -c \"print('Hello, World!')\"",
		}
		inputJSON, _ := json.Marshal(bashInput)

		bashPart := anthropic.BetaContentBlockUnion{
			Type:  "server_tool_use",
			Name:  "bash_code_execution",
			Input: inputJSON,
		}

		// Test the function
		result := createExecutableCodePartFromToolUse(bashPart)

		// Verify it's a custom part
		if !result.IsCustom() {
			t.Error("Expected custom part for executable code")
		}

		// Extract the executable code
		execCode := ToExecutableCode(result)
		if execCode == nil {
			t.Error("Expected to extract executable code")
		}

		if execCode.Language != "bash" {
			t.Errorf("Expected language 'bash', got '%s'", execCode.Language)
		}

		if execCode.Code != "python -c \"print('Hello, World!')\"" {
			t.Errorf("Expected code to match input command, got '%s'", execCode.Code)
		}
	})

	t.Run("CreateCodeExecutionResultPart", func(t *testing.T) {
		// Create a mock bash_code_execution_tool_result part with realistic Python output
		resultPart := anthropic.BetaContentBlockUnion{
			Type: "bash_code_execution_tool_result",
			Text: "Square root of 46 = 6.782329983125268\nRounded to 6 decimal places: 6.782330\nVerification: 6.782330² = 46.000001",
		}

		// Test the function
		result := createCodeExecutionResultPartFromToolResult(resultPart)

		// Verify it's a custom part
		if !result.IsCustom() {
			t.Error("Expected custom part for code execution result")
		}

		// Extract the code execution result
		execResult := ToCodeExecutionResult(result)
		if execResult == nil {
			t.Error("Expected to extract code execution result")
		}

		if execResult.Outcome != "success" {
			t.Errorf("Expected outcome 'success', got '%s'", execResult.Outcome)
		}

		expectedOutput := "Square root of 46 = 6.782329983125268\nRounded to 6 decimal places: 6.782330\nVerification: 6.782330² = 46.000001"
		if execResult.Output != expectedOutput {
			t.Errorf("Expected output to match Python execution result, got '%s'", execResult.Output)
		}
	})

	t.Run("CreateCodeExecutionResultPartWithEmptyText", func(t *testing.T) {
		// Test what happens when Text field is empty (this might be the issue)
		resultPart := anthropic.BetaContentBlockUnion{
			Type: "bash_code_execution_tool_result",
			Text: "", // Empty text - this might be the problem
			ID:   "test_id_123",
		}

		// Test the function
		result := createCodeExecutionResultPartFromToolResult(resultPart)

		// Extract the code execution result
		execResult := ToCodeExecutionResult(result)
		if execResult == nil {
			t.Error("Expected to extract code execution result")
		}

		// Should fall back to a meaningful message with ID
		if !strings.Contains(execResult.Output, "test_id_123") {
			t.Errorf("Expected output to contain ID when text is empty, got '%s'", execResult.Output)
		}
	})

	t.Run("CreateTextEditorCodePart", func(t *testing.T) {
		// Create a mock text_editor_code_execution part for creating a Python file
		editorInput := map[string]any{
			"command":   "create",
			"path":      "hello.py",
			"file_text": "print('Hello from Python!')",
		}
		inputJSON, _ := json.Marshal(editorInput)

		editorPart := anthropic.BetaContentBlockUnion{
			Type:  "server_tool_use",
			Name:  "text_editor_code_execution",
			Input: inputJSON,
		}

		// Test the function
		result := createExecutableCodePartFromToolUse(editorPart)

		// Verify it's a custom part
		if !result.IsCustom() {
			t.Error("Expected custom part for executable code")
		}

		// Extract the executable code
		execCode := ToExecutableCode(result)
		if execCode == nil {
			t.Error("Expected to extract executable code")
		}

		if execCode.Language != "python" {
			t.Errorf("Expected language 'python', got '%s'", execCode.Language)
		}

		if execCode.Code != "print('Hello from Python!')" {
			t.Errorf("Expected code to match file content, got '%s'", execCode.Code)
		}
	})

	t.Run("ErrorDetection", func(t *testing.T) {
		// Test error detection in bash results
		errorPart := anthropic.BetaContentBlockUnion{
			Type: "bash_code_execution_tool_result",
			Text: "Error: command not found",
		}

		result := createCodeExecutionResultPartFromToolResult(errorPart)
		execResult := ToCodeExecutionResult(result)

		if execResult.Outcome != "error" {
			t.Errorf("Expected outcome 'error' for error text, got '%s'", execResult.Outcome)
		}
	})
}

func TestBetaResponseConversion(t *testing.T) {
	// Test the full Beta response conversion with code execution parts
	t.Run("FullBetaResponseWithCodeExecution", func(t *testing.T) {
		// Create a mock Beta message with code execution content
		bashInput := map[string]any{
			"command": "ls -la",
		}
		inputJSON, _ := json.Marshal(bashInput)

		betaMessage := &anthropic.BetaMessage{
			StopReason: anthropic.BetaStopReasonEndTurn,
			Content: []anthropic.BetaContentBlockUnion{
				{
					Type: "text",
					Text: "I'll run the ls command to list the files:",
				},
				{
					Type:  "server_tool_use",
					Name:  "bash_code_execution",
					Input: inputJSON,
				},
				{
					Type: "bash_code_execution_tool_result",
					Text: "total 8\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 .\ndrwxr-xr-x 3 user user 4096 Jan 1 11:00 ..\n-rw-r--r-- 1 user user  220 Jan 1 12:00 file.txt",
				},
				{
					Type: "text",
					Text: "The directory contains one file: file.txt",
				},
			},
			Usage: anthropic.BetaUsage{
				InputTokens:  50,
				OutputTokens: 100,
			},
		}

		// Convert to Genkit response
		response, err := anthropicBetaToGenkitResponse(betaMessage)
		if err != nil {
			t.Fatalf("Failed to convert Beta response: %v", err)
		}

		// Verify the response structure
		if response.FinishReason != ai.FinishReasonStop {
			t.Errorf("Expected finish reason 'stop', got '%s'", response.FinishReason)
		}

		if len(response.Message.Content) != 4 {
			t.Errorf("Expected 4 content parts, got %d", len(response.Message.Content))
		}

		// Check that we have the right types of parts
		var hasText, hasExecutableCode, hasCodeResult bool
		for _, part := range response.Message.Content {
			if part.IsText() {
				hasText = true
			}
			if part.IsCustom() {
				if ToExecutableCode(part) != nil {
					hasExecutableCode = true
				}
				if ToCodeExecutionResult(part) != nil {
					hasCodeResult = true
				}
			}
		}

		if !hasText {
			t.Error("Expected to find text parts")
		}
		if !hasExecutableCode {
			t.Error("Expected to find executable code part")
		}
		if !hasCodeResult {
			t.Error("Expected to find code execution result part")
		}
	})
}

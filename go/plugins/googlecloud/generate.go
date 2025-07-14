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

package googlecloud

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// GenerateTelemetry implements telemetry collection for model generate actions
type GenerateTelemetry struct {
	actionCounter    *MetricCounter   // genkit/ai/generate/requests
	latencies        *MetricHistogram // genkit/ai/generate/latency
	inputCharacters  *MetricCounter   // genkit/ai/generate/input/characters
	inputTokens      *MetricCounter   // genkit/ai/generate/input/tokens
	inputImages      *MetricCounter   // genkit/ai/generate/input/images
	outputCharacters *MetricCounter   // genkit/ai/generate/output/characters
	outputTokens     *MetricCounter   // genkit/ai/generate/output/tokens
	outputImages     *MetricCounter   // genkit/ai/generate/output/images
	cloudLogger      CloudLogger      // For structured logging to Google Cloud
}

// NewGenerateTelemetry creates a new generate telemetry module with all required metrics
func NewGenerateTelemetry() *GenerateTelemetry {
	// Use the namespace wrapper from metrics.go
	n := func(name string) string { return internalMetricNamespaceWrap("ai", name) }

	return &GenerateTelemetry{
		actionCounter: NewMetricCounter(n("generate/requests"), MetricCounterOptions{
			Description: "Counts calls to genkit generate actions.",
			Unit:        "1",
		}),
		latencies: NewMetricHistogram(n("generate/latency"), MetricHistogramOptions{
			Description: "Latencies when interacting with a Genkit model.",
			Unit:        "ms",
		}),
		inputCharacters: NewMetricCounter(n("generate/input/characters"), MetricCounterOptions{
			Description: "Counts input characters to any Genkit model.",
			Unit:        "1",
		}),
		inputTokens: NewMetricCounter(n("generate/input/tokens"), MetricCounterOptions{
			Description: "Counts input tokens to a Genkit model.",
			Unit:        "1",
		}),
		inputImages: NewMetricCounter(n("generate/input/images"), MetricCounterOptions{
			Description: "Counts input images to a Genkit model.",
			Unit:        "1",
		}),
		outputCharacters: NewMetricCounter(n("generate/output/characters"), MetricCounterOptions{
			Description: "Counts output characters from a Genkit model.",
			Unit:        "1",
		}),
		outputTokens: NewMetricCounter(n("generate/output/tokens"), MetricCounterOptions{
			Description: "Counts output tokens from a Genkit model.",
			Unit:        "1",
		}),
		outputImages: NewMetricCounter(n("generate/output/images"), MetricCounterOptions{
			Description: "Count output images from a Genkit model.",
			Unit:        "1",
		}),
		cloudLogger: NewNoOpCloudLogger(), // Will be set via SetCloudLogger
	}
}

// SetCloudLogger implements the Telemetry interface
func (g *GenerateTelemetry) SetCloudLogger(logger CloudLogger) {
	g.cloudLogger = logger
}

// Tick processes a span for generate telemetry
func (g *GenerateTelemetry) Tick(span sdktrace.ReadOnlySpan, logInputOutput bool, projectID string) {
	attributes := span.Attributes()

	// DEBUG: Log all spans being processed
	slog.Info("GenerateTelemetry.Tick: Processing span",
		"span_name", span.Name(),
		"span_kind", span.SpanKind(),
		"attributes_count", len(attributes))

	// DEBUG: Log specific attributes we're looking for
	subtype := extractStringAttribute(attributes, "genkit:metadata:subtype")
	spanName := extractStringAttribute(attributes, "genkit:name")
	slog.Info("GenerateTelemetry.Tick: Key attributes",
		"subtype", subtype,
		"genkit:name", spanName)

	// Only process spans that are model actions (genkit:metadata:subtype = "model")
	if subtype != "model" {
		slog.Info("GenerateTelemetry.Tick: Skipping span - not a model action", "subtype", subtype)
		return
	}

	slog.Info("GenerateTelemetry.Tick: Processing model span!", "subtype", subtype)

	// Extract key span data
	modelName := truncate(extractStringAttribute(attributes, "genkit:name"), 1024)
	path := extractStringAttribute(attributes, "genkit:path")
	inputStr := extractStringAttribute(attributes, "genkit:input")
	outputStr := extractStringAttribute(attributes, "genkit:output")

	// Parse input/output JSON
	var input GenerateRequestData
	var output GenerateResponseData

	if inputStr != "" {
		if err := json.Unmarshal([]byte(inputStr), &input); err != nil {
			// If JSON parsing fails, continue without input data
			slog.Debug("Failed to parse generate input JSON", "error", err)
		}
	}

	if outputStr != "" {
		if err := json.Unmarshal([]byte(outputStr), &output); err != nil {
			// If JSON parsing fails, continue without output data
			slog.Debug("Failed to parse generate output JSON", "error", err)
		}
	}

	// Extract error information
	errName := g.extractErrorName(span)

	// Extract feature name (from flow context or path)
	featureName := truncate(g.extractFeatureName(attributes, path))

	// Extract session and thread info
	sessionId := extractStringAttribute(attributes, "genkit:sessionId")
	threadName := extractStringAttribute(attributes, "genkit:threadName")

	// Log configuration info
	if input.Config != nil {
		g.recordGenerateActionConfigLogs(span, modelName, featureName, path, &input, projectID, sessionId, threadName)
	}

	// Log input content if available and enabled
	if inputStr != "" && logInputOutput {
		g.recordGenerateActionInputLogs(span, modelName, featureName, path, &input, projectID, sessionId, threadName)
	}

	// Log output content if available and enabled
	if outputStr != "" && logInputOutput {
		g.recordGenerateActionOutputLogs(span, modelName, featureName, path, &output, projectID, sessionId, threadName)
	}
	slog.Info("GenerateTelemetry.Tick: Feature extraction debug",
		"path", path,
		"extracted_feature", featureName)
	if featureName == "" || featureName == "<unknown>" {
		featureName = "generate"
		slog.Info("GenerateTelemetry.Tick: Using fallback feature name", "featureName", featureName)
	}

	// Record metrics if we have input data
	if inputStr != "" {
		g.recordGenerateActionMetrics(modelName, featureName, path, &output, errName)
	}
}

// recordGenerateActionMetrics records all metrics for a generate action
func (g *GenerateTelemetry) recordGenerateActionMetrics(modelName, featureName, path string, output *GenerateResponseData, errName string) {
	status := "success"
	if errName != "" {
		status = "failure"
	}

	// Shared dimensions for metrics
	dimensions := map[string]interface{}{
		"modelName":     modelName,
		"featureName":   featureName,
		"path":          path,
		"status":        status,
		"source":        "go",
		"sourceVersion": "1.0.0", // TODO: Get actual version
	}

	// Record request count
	errorDimensions := make(map[string]interface{})
	for k, v := range dimensions {
		errorDimensions[k] = v
	}
	if errName != "" {
		errorDimensions["error"] = errName
	}
	g.actionCounter.Add(1, errorDimensions)

	// Record latency if available
	if output != nil && output.LatencyMs > 0 {
		g.latencies.Record(output.LatencyMs, dimensions)
	}

	// Record usage metrics if available
	if output != nil && output.Usage != nil {
		usage := output.Usage
		g.inputTokens.Add(usage.InputTokens, dimensions)
		g.inputCharacters.Add(usage.InputCharacters, dimensions)
		g.inputImages.Add(usage.InputImages, dimensions)
		g.outputTokens.Add(usage.OutputTokens, dimensions)
		g.outputCharacters.Add(usage.OutputCharacters, dimensions)
		g.outputImages.Add(usage.OutputImages, dimensions)
	}
}

// recordGenerateActionConfigLogs logs configuration information
func (g *GenerateTelemetry) recordGenerateActionConfigLogs(span sdktrace.ReadOnlySpan, model, featureName, qualifiedPath string, input *GenerateRequestData, projectID, sessionID, threadName string) {
	path := truncatePath(toDisplayPath(qualifiedPath))
	sharedMetadata := g.createCommonLogAttributes(span, projectID)

	logData := map[string]interface{}{
		"model":         model,
		"path":          path,
		"qualifiedPath": qualifiedPath,
		"featureName":   featureName,
		"sessionId":     sessionID,
		"threadName":    threadName,
		"source":        "go",
		"sourceVersion": "1.0.0",
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		logData[k] = v
	}

	// Add config details if available
	if input.Config != nil {
		logData["maxOutputTokens"] = input.Config.MaxOutputTokens
		logData["stopSequences"] = input.Config.StopSequences
	}

	// Send to Google Cloud Logging
	message := fmt.Sprintf("Config[%s, %s]", path, model)
	g.cloudLogger.LogStructured(context.Background(), message, logData)

	// Also log locally for debugging
	slog.Info(message, "data", logData)
}

// recordGenerateActionInputLogs logs input information
func (g *GenerateTelemetry) recordGenerateActionInputLogs(span sdktrace.ReadOnlySpan, model, featureName, qualifiedPath string, input *GenerateRequestData, projectID, sessionID, threadName string) {
	if input.Messages == nil {
		return
	}

	path := truncatePath(toDisplayPath(qualifiedPath))
	sharedMetadata := g.createCommonLogAttributes(span, projectID)

	baseLogData := map[string]interface{}{
		"model":         model,
		"path":          path,
		"qualifiedPath": qualifiedPath,
		"featureName":   featureName,
		"sessionId":     sessionID,
		"threadName":    threadName,
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		baseLogData[k] = v
	}

	messages := len(input.Messages)
	for msgIdx, msg := range input.Messages {
		parts := len(msg.Content)
		for partIdx, part := range msg.Content {
			logData := make(map[string]interface{})
			for k, v := range baseLogData {
				logData[k] = v
			}

			partCounts := g.toPartCounts(partIdx, parts, msgIdx, messages)
			logData["content"] = g.toPartLogContent(&part)
			logData["role"] = msg.Role
			logData["partIndex"] = partIdx
			logData["totalParts"] = parts
			logData["messageIndex"] = msgIdx
			logData["totalMessages"] = messages

			// Send to Google Cloud Logging
			message := fmt.Sprintf("Input[%s, %s] %s", path, model, partCounts)
			g.cloudLogger.LogStructured(context.Background(), message, logData)

			// Also log locally for debugging
			slog.Info(message, "data", logData)
		}
	}
}

// recordGenerateActionOutputLogs logs output information
func (g *GenerateTelemetry) recordGenerateActionOutputLogs(span sdktrace.ReadOnlySpan, model, featureName, qualifiedPath string, output *GenerateResponseData, projectID, sessionID, threadName string) {
	path := truncatePath(toDisplayPath(qualifiedPath))
	sharedMetadata := g.createCommonLogAttributes(span, projectID)

	baseLogData := map[string]interface{}{
		"model":         model,
		"path":          path,
		"qualifiedPath": qualifiedPath,
		"featureName":   featureName,
		"sessionId":     sessionID,
		"threadName":    threadName,
	}

	// Add shared metadata
	for k, v := range sharedMetadata {
		baseLogData[k] = v
	}

	// Handle message from either direct message or first candidate
	var message *Message
	if output.Message != nil {
		message = output.Message
	} else if len(output.Candidates) > 0 && output.Candidates[0].Message != nil {
		message = output.Candidates[0].Message
	}

	if message != nil && message.Content != nil {
		parts := len(message.Content)
		for partIdx, part := range message.Content {
			logData := make(map[string]interface{})
			for k, v := range baseLogData {
				logData[k] = v
			}

			partCounts := g.toPartCounts(partIdx, parts, 0, 1)

			if output.FinishMessage != "" {
				logData["finishMessage"] = truncate(output.FinishMessage)
			}

			logData["content"] = g.toPartLogContent(&part)
			logData["role"] = message.Role
			logData["partIndex"] = partIdx
			logData["totalParts"] = parts
			logData["candidateIndex"] = 0
			logData["totalCandidates"] = 1
			logData["messageIndex"] = 0
			logData["finishReason"] = output.FinishReason

			// Send to Google Cloud Logging
			message := fmt.Sprintf("Output[%s, %s] %s", path, model, partCounts)
			g.cloudLogger.LogStructured(context.Background(), message, logData)

			// Also log locally for debugging
			slog.Info(message, "data", logData)
		}
	}
}

// Helper functions

func (g *GenerateTelemetry) extractErrorName(span sdktrace.ReadOnlySpan) string {
	if span.Status().Code == codes.Error {
		return span.Status().Description
	}

	// Check events for error information
	for _, event := range span.Events() {
		if event.Name == "exception" {
			for _, attr := range event.Attributes {
				if string(attr.Key) == "exception.type" {
					return attr.Value.AsString()
				}
			}
		}
	}
	return ""
}

func (g *GenerateTelemetry) extractFeatureName(attributes []attribute.KeyValue, path string) string {
	// Try to get from flow context first
	flowName := extractStringAttribute(attributes, "genkit:metadata:flow:name")
	if flowName != "" {
		return flowName
	}

	// Extract from path as fallback
	return extractOuterFeatureNameFromPath(path)
}

func (g *GenerateTelemetry) createCommonLogAttributes(span sdktrace.ReadOnlySpan, projectID string) map[string]interface{} {
	spanContext := span.SpanContext()
	return map[string]interface{}{
		"logging.googleapis.com/trace":         fmt.Sprintf("projects/%s/traces/%s", projectID, spanContext.TraceID().String()),
		"logging.googleapis.com/spanId":        spanContext.SpanID().String(),
		"logging.googleapis.com/trace_sampled": spanContext.IsSampled(),
	}
}

func (g *GenerateTelemetry) toPartCounts(partOrdinal, parts, msgOrdinal, messages int) string {
	if parts > 1 && messages > 1 {
		return fmt.Sprintf("(part %s in message %s)", g.xOfY(partOrdinal, parts), g.xOfY(msgOrdinal, messages))
	}
	if parts > 1 {
		return fmt.Sprintf("(part %s)", g.xOfY(partOrdinal, parts))
	}
	if messages > 1 {
		return fmt.Sprintf("(message %s)", g.xOfY(msgOrdinal, messages))
	}
	return ""
}

func (g *GenerateTelemetry) xOfY(x, y int) string {
	return fmt.Sprintf("%d of %d", x+1, y)
}

func (g *GenerateTelemetry) toPartLogContent(part *Part) string {
	if part.Text != "" {
		return truncate(part.Text)
	}
	if part.Data != nil {
		data, _ := json.Marshal(part.Data)
		return truncate(string(data))
	}
	if part.Media != nil {
		return g.toPartLogMedia(part.Media)
	}
	if part.ToolRequest != nil {
		return g.toPartLogToolRequest(part.ToolRequest)
	}
	if part.ToolResponse != nil {
		return g.toPartLogToolResponse(part.ToolResponse)
	}
	if part.Custom != nil {
		data, _ := json.Marshal(part.Custom)
		return truncate(string(data))
	}
	return "<unknown format>"
}

func (g *GenerateTelemetry) toPartLogMedia(media *MediaPart) string {
	if strings.HasPrefix(media.URL, "data:") {
		splitIdx := strings.Index(media.URL, "base64,")
		if splitIdx < 0 {
			return "<unknown media format>"
		}
		prefix := media.URL[:splitIdx+7]
		hasher := sha256.New()
		hasher.Write([]byte(media.URL[splitIdx+7:]))
		hashedContent := hex.EncodeToString(hasher.Sum(nil))
		return fmt.Sprintf("%s<sha256(%s)>", prefix, hashedContent)
	}
	return truncate(media.URL)
}

func (g *GenerateTelemetry) toPartLogToolRequest(tool *ToolRequestPart) string {
	var inputText string
	if str, ok := tool.Input.(string); ok {
		inputText = str
	} else {
		data, _ := json.Marshal(tool.Input)
		inputText = string(data)
	}
	return truncate(fmt.Sprintf("Tool request: %s, ref: %s, input: %s", tool.Name, tool.Ref, inputText))
}

func (g *GenerateTelemetry) toPartLogToolResponse(tool *ToolResponsePart) string {
	var outputText string
	if str, ok := tool.Output.(string); ok {
		outputText = str
	} else {
		data, _ := json.Marshal(tool.Output)
		outputText = string(data)
	}
	return truncate(fmt.Sprintf("Tool response: %s, ref: %s, output: %s", tool.Name, tool.Ref, outputText))
}

// Utility functions

// toDisplayPath converts qualified paths to display paths
func toDisplayPath(qualifiedPath string) string {
	if qualifiedPath == "" {
		return "<unknown>"
	}

	// Extract the display path from qualified path
	return qualifiedPath
}

func truncatePath(path string) string {
	displayPath := toDisplayPath(path)
	return truncate(displayPath, MaxPathLength)
}

func extractOuterFeatureNameFromPath(path string) string {
	if path == "" || path == "<unknown>" {
		return "<unknown>"
	}

	parts := strings.Split(path, "/")
	if len(parts) == 0 {
		return "<unknown>"
	}

	// Skip empty parts (caused by leading slash) and find first meaningful part
	for _, part := range parts {
		if part != "" {
			// Extract feature name from pattern like "{myFlow,t:flow}"
			if strings.HasPrefix(part, "{") && strings.Contains(part, ",t:") {
				// Find the name before the first comma
				commaIdx := strings.Index(part, ",")
				if commaIdx > 1 {
					return part[1:commaIdx] // Remove the opening { and everything after comma
				}
			}
			return part // Return first non-empty part as fallback
		}
	}
	return "<unknown>"
}

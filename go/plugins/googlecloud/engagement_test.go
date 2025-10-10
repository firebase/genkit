// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googlecloud

import (
	"bytes"
	"context"
	"fmt"
	"log/slog"
	"testing"

	"github.com/stretchr/testify/assert"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/metricdata"
)

// setupLogCapture redirects slog to a buffer and returns the buffer for reading logs
func setupLogCapture(t *testing.T) *bytes.Buffer {
	var buf bytes.Buffer
	originalHandler := slog.Default()

	// Create a text handler that writes to our buffer
	handler := slog.NewTextHandler(&buf, &slog.HandlerOptions{
		Level: slog.LevelDebug,
	})
	slog.SetDefault(slog.New(handler))

	// Restore original logger when test ends
	t.Cleanup(func() {
		slog.SetDefault(originalHandler)
	})

	return &buf
}

func TestNewEngagementTelemetry(t *testing.T) {
	engTel := NewEngagementTelemetry()

	assert.NotNil(t, engTel)
	assert.NotNil(t, engTel.feedbackCounter)
	assert.NotNil(t, engTel.acceptanceCounter)
}

func TestEngagementTelemetry_extractTraceName(t *testing.T) {
	engTel := NewEngagementTelemetry()

	testCases := []struct {
		name     string
		path     string
		expected string
	}{
		{
			name:     "simple action path",
			path:     "/testFlow/{myAction,t:action}",
			expected: "myAction,t:action",
		},
		{
			name:     "realistic genkit format",
			path:     "/{testFlow,t:flow}/{myAction,t:action}",
			expected: "myAction,t:action",
		},
		{
			name:     "nested path - extracts final action",
			path:     "/parentFlow/{step1,t:flowStep}/{finalAction,t:action}",
			expected: "finalAction,t:action",
		},
		{
			name:     "complex path with multiple components",
			path:     "/flow/{component1,t:step}/{component2,t:action}/{component3,t:final}",
			expected: "component3,t:final",
		},
		{
			name:     "empty path",
			path:     "",
			expected: "<unknown>",
		},
		{
			name:     "unknown path marker",
			path:     "<unknown>",
			expected: "<unknown>",
		},
		{
			name:     "path without brackets",
			path:     "/simple/path/without/brackets",
			expected: "<unknown>",
		},
		{
			name:     "malformed brackets",
			path:     "/flow/{incomplete",
			expected: "<unknown>",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			attrs := []attribute.KeyValue{
				attribute.String("genkit:path", tc.path),
			}
			result := engTel.extractTraceName(attrs)
			assert.Equal(t, tc.expected, result)
		})
	}
}

// TestEngagementTelemetry_PipelineIntegration verifies that engagement telemetry
// receives the correct colon-based attributes before normalization in the pipeline
func TestEngagementTelemetry_PipelineIntegration(t *testing.T) {
	// This test verifies that engagement telemetry works correctly in the full pipeline,
	// receiving colon-based attributes before they get normalized to slash-based for export

	engTel := NewEngagementTelemetry()
	f := newTestFixture(t, true, engTel) // Enable logging for engagement telemetry tests

	// Set up log capture
	logBuf := setupLogCapture(t)

	// Create span using the TracerProvider - this triggers the full pipeline
	ctx := context.Background()
	_, span := f.tracer.Start(ctx, "test-span")

	span.SetAttributes(
		attribute.String("genkit:type", "userEngagement"), // Required for telemetry processing
		attribute.String("genkit:metadata:subtype", "userFeedback"),
		attribute.String("genkit:path", "/{testFlow,t:flow}/{myAction,t:action}"),
		attribute.String("genkit:metadata:feedbackValue", "positive"),
	)

	span.End() // This triggers the pipeline

	// Get captured logs
	logOutput := logBuf.String()

	// Verify engagement telemetry worked
	assert.Contains(t, logOutput, "UserFeedback[myAction,t:action]")
	assert.Contains(t, logOutput, "feedbackValue:positive")

	// Verify the span was exported with normalized attributes (slash-based)
	spans := f.waitAndGetSpans()
	assert.Len(t, spans, 1)
	exportedSpan := spans[0]

	// The exported span should have normalized attributes
	attrs := exportedSpan.Attributes()
	attributeKeys := make([]string, len(attrs))
	for i, attr := range attrs {
		attributeKeys[i] = string(attr.Key)
	}

	// The span will have normalized attributes (with slashes) for export
	assert.Contains(t, attributeKeys, "genkit/metadata/subtype")
	assert.Contains(t, attributeKeys, "genkit/path")
	assert.Contains(t, attributeKeys, "genkit/metadata/feedbackValue")
	// Verify all colon-based attributes were normalized to slash-based
	assert.NotContains(t, attributeKeys, "genkit:metadata:subtype")
	assert.NotContains(t, attributeKeys, "genkit:path")
	assert.NotContains(t, attributeKeys, "genkit:metadata:feedbackValue")
}

func TestEngagementTelemetry_MetricCapture(t *testing.T) {
	// Test that verifies we can capture and verify metric calls using OTel's built-in test reader

	testCases := []struct {
		name                    string
		attrs                   map[string]string
		expectFeedbackMetrics   bool
		expectAcceptanceMetrics bool
		expectedFeedbackValue   string
		expectedAcceptanceValue string
		expectedName            string
		expectedHasText         interface{}
	}{
		{
			name: "user feedback captures metrics correctly",
			attrs: map[string]string{
				"genkit:type":                   "userEngagement",
				"genkit:metadata:subtype":       "userFeedback",
				"genkit:path":                   "/{chatFlow,t:flow}/{generateResponse,t:action}",
				"genkit:metadata:feedbackValue": "positive",
				"genkit:metadata:textFeedback":  "Great response!",
			},
			expectFeedbackMetrics:   true,
			expectAcceptanceMetrics: false,
			expectedFeedbackValue:   "positive",
			expectedName:            "generateResponse,t:action",
			expectedHasText:         true,
		},
		{
			name: "user feedback without text",
			attrs: map[string]string{
				"genkit:type":                   "userEngagement",
				"genkit:metadata:subtype":       "userFeedback",
				"genkit:path":                   "/{testFlow,t:flow}/{myAction,t:action}",
				"genkit:metadata:feedbackValue": "negative",
			},
			expectFeedbackMetrics:   true,
			expectAcceptanceMetrics: false,
			expectedFeedbackValue:   "negative",
			expectedName:            "myAction,t:action",
			expectedHasText:         false,
		},
		{
			name: "user acceptance captures metrics correctly",
			attrs: map[string]string{
				"genkit:type":                     "userEngagement",
				"genkit:metadata:subtype":         "userAcceptance",
				"genkit:path":                     "/{codeAssistant,t:flow}/{suggestCode,t:action}",
				"genkit:metadata:acceptanceValue": "accepted",
			},
			expectFeedbackMetrics:   false,
			expectAcceptanceMetrics: true,
			expectedAcceptanceValue: "accepted",
			expectedName:            "suggestCode,t:action",
		},
		{
			name: "unknown subtype captures no metrics",
			attrs: map[string]string{
				"genkit:type":             "userEngagement",
				"genkit:metadata:subtype": "unknownType",
				"genkit:path":             "/{testFlow,t:flow}/{myAction,t:action}",
			},
			expectFeedbackMetrics:   false,
			expectAcceptanceMetrics: false,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			// Create a fresh ManualReader for each test case to avoid accumulation
			reader := sdkmetric.NewManualReader()

			// Create a MeterProvider with the test reader
			testMeterProvider := sdkmetric.NewMeterProvider(sdkmetric.WithReader(reader))

			// Set the global meter provider temporarily for the test
			originalProvider := otel.GetMeterProvider()
			otel.SetMeterProvider(testMeterProvider)
			defer otel.SetMeterProvider(originalProvider)

			// Create engagement telemetry (it will use the global meter provider)
			engTel := NewEngagementTelemetry()
			f := newTestFixture(t, true, engTel) // Enable logging for engagement telemetry tests

			f.mockExporter.Reset()

			// Create span using the TracerProvider - this will flow through engagement telemetry
			ctx := context.Background()
			_, span := f.tracer.Start(ctx, "test-span")

			for key, value := range tc.attrs {
				span.SetAttributes(attribute.String(key, value))
			}

			span.End() // This triggers the pipeline including engagement telemetry

			// Wait for span to be processed
			spans := f.waitAndGetSpans()
			assert.Len(t, spans, 1)

			// Collect metrics using the manual reader
			var resourceMetrics metricdata.ResourceMetrics
			err := reader.Collect(ctx, &resourceMetrics)
			assert.NoError(t, err)

			// Verify metrics
			if tc.expectFeedbackMetrics {
				feedbackMetric := findMetric(&resourceMetrics, "genkit/engagement/feedback")
				assert.NotNil(t, feedbackMetric, "Expected feedback metric to be recorded")
				if feedbackMetric != nil {
					verifyCounterMetric(t, feedbackMetric, map[string]interface{}{
						"name":    tc.expectedName,
						"value":   tc.expectedFeedbackValue,
						"hasText": tc.expectedHasText,
						"source":  "go",
					})
				}
			}

			if tc.expectAcceptanceMetrics {
				acceptanceMetric := findMetric(&resourceMetrics, "genkit/engagement/acceptance")
				assert.NotNil(t, acceptanceMetric, "Expected acceptance metric to be recorded")
				if acceptanceMetric != nil {
					verifyCounterMetric(t, acceptanceMetric, map[string]interface{}{
						"name":   tc.expectedName,
						"value":  tc.expectedAcceptanceValue,
						"source": "go",
					})
				}
			}

			if !tc.expectFeedbackMetrics && !tc.expectAcceptanceMetrics {
				// Should have no engagement metrics
				feedbackMetric := findMetric(&resourceMetrics, "genkit/engagement/feedback")
				acceptanceMetric := findMetric(&resourceMetrics, "genkit/engagement/acceptance")
				assert.Nil(t, feedbackMetric, "Should not have feedback metrics")
				assert.Nil(t, acceptanceMetric, "Should not have acceptance metrics")
			}
		})
	}
}

// Helper functions for metric verification

func findMetric(rm *metricdata.ResourceMetrics, name string) *metricdata.Metrics {
	for _, sm := range rm.ScopeMetrics {
		for _, metric := range sm.Metrics {
			if metric.Name == name {
				return &metric
			}
		}
	}
	return nil
}

func verifyCounterMetric(t *testing.T, metric *metricdata.Metrics, expectedAttrs map[string]interface{}) {
	// Verify it's a counter/sum metric
	sum, ok := metric.Data.(metricdata.Sum[int64])
	assert.True(t, ok, "Expected metric to be a Sum[int64]")

	// Should have exactly one data point for our test
	assert.Len(t, sum.DataPoints, 1, "Expected exactly one data point")

	if len(sum.DataPoints) > 0 {
		dp := sum.DataPoints[0]

		// Verify the value (should be 1 for counter)
		assert.Equal(t, int64(1), dp.Value, "Expected counter value to be 1")

		// Verify attributes
		for expectedKey, expectedValue := range expectedAttrs {
			found := false
			for _, attr := range dp.Attributes.ToSlice() {
				if string(attr.Key) == expectedKey {
					found = true
					switch v := expectedValue.(type) {
					case string:
						assert.Equal(t, v, attr.Value.AsString(), "Attribute %s mismatch", expectedKey)
					case bool:
						assert.Equal(t, v, attr.Value.AsBool(), "Attribute %s mismatch", expectedKey)
					case int64:
						assert.Equal(t, v, attr.Value.AsInt64(), "Attribute %s mismatch", expectedKey)
					default:
						assert.Equal(t, fmt.Sprintf("%v", v), attr.Value.AsString(), "Attribute %s mismatch", expectedKey)
					}
					break
				}
			}
			assert.True(t, found, "Expected attribute %s not found", expectedKey)
		}
	}
}
func TestEngagementTelemetry_ComprehensiveScenarios(t *testing.T) {
	// Test multiple engagement telemetry scenarios using the proper pipeline integration

	engTel := NewEngagementTelemetry()
	f := newTestFixture(t, true, engTel) // Enable logging for engagement telemetry tests

	testCases := []struct {
		name         string
		attrs        map[string]string
		expectLog    bool
		expectedText string
	}{
		{
			name: "user feedback with text",
			attrs: map[string]string{
				"genkit:type":                   "userEngagement",
				"genkit:metadata:subtype":       "userFeedback",
				"genkit:path":                   "/{chatFlow,t:flow}/{generateResponse,t:action}",
				"genkit:metadata:feedbackValue": "positive",
				"genkit:metadata:textFeedback":  "Great response!",
				"genkit:sessionId":              "session-123",
			},
			expectLog:    true,
			expectedText: "UserFeedback[generateResponse,t:action]",
		},
		{
			name: "user feedback without text",
			attrs: map[string]string{
				"genkit:type":                   "userEngagement",
				"genkit:metadata:subtype":       "userFeedback",
				"genkit:path":                   "/{testFlow,t:flow}/{myAction,t:action}",
				"genkit:metadata:feedbackValue": "negative",
				"genkit:sessionId":              "session-789",
			},
			expectLog:    true,
			expectedText: "UserFeedback[myAction,t:action]",
		},
		{
			name: "user acceptance",
			attrs: map[string]string{
				"genkit:type":                     "userEngagement",
				"genkit:metadata:subtype":         "userAcceptance",
				"genkit:path":                     "/{codeAssistant,t:flow}/{suggestCode,t:action}",
				"genkit:metadata:acceptanceValue": "accepted",
				"genkit:sessionId":                "session-456",
			},
			expectLog:    true,
			expectedText: "UserAcceptance[suggestCode,t:action]",
		},
		{
			name: "unknown subtype",
			attrs: map[string]string{
				"genkit:type":             "userEngagement",
				"genkit:metadata:subtype": "unknownType",
				"genkit:path":             "/{testFlow,t:flow}/{myAction,t:action}",
			},
			expectLog:    false,
			expectedText: "",
		},
		{
			name: "no subtype",
			attrs: map[string]string{
				"genkit:type": "userEngagement",
				"genkit:path": "/{testFlow,t:flow}/{myAction,t:action}",
			},
			expectLog:    false,
			expectedText: "",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			f.mockExporter.Reset()

			// Set up log capture
			logBuf := setupLogCapture(t)

			// Create span using the TracerProvider - this triggers the full pipeline
			ctx := context.Background()
			_, span := f.tracer.Start(ctx, "test-span")

			for key, value := range tc.attrs {
				span.SetAttributes(attribute.String(key, value))
			}

			span.End() // This triggers the pipeline including engagement telemetry

			// Get captured logs
			logOutput := logBuf.String()

			// Verify spans were processed
			spans := f.waitAndGetSpans()
			assert.Len(t, spans, 1)

			// Check logging behavior
			if tc.expectLog {
				assert.Contains(t, logOutput, tc.expectedText,
					"Expected log containing %q but got: %q", tc.expectedText, logOutput)
			} else {
				// Should not contain engagement logs
				assert.NotContains(t, logOutput, "UserFeedback[", "Unexpected UserFeedback log")
				assert.NotContains(t, logOutput, "UserAcceptance[", "Unexpected UserAcceptance log")
			}
		})
	}
}

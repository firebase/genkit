// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googlecloud

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/metricdata"
)

func TestNewPathTelemetry(t *testing.T) {
	pathTel := NewPathTelemetry()

	assert.NotNil(t, pathTel)
	assert.NotNil(t, pathTel.pathCounter)
	assert.NotNil(t, pathTel.pathLatencies)
}

// TestPathTelemetry_PipelineIntegration verifies that path telemetry
// processes failing spans correctly in the full pipeline
func TestPathTelemetry_PipelineIntegration(t *testing.T) {
	// This test verifies that path telemetry works correctly in the full pipeline,
	// only processing failing spans that are failure sources

	pathTel := NewPathTelemetry()
	f := newTestFixture(t, pathTel)

	// Set up log capture
	logBuf := setupLogCapture(t)

	// Create span using the TracerProvider - this triggers the full pipeline
	ctx := context.Background()
	_, span := f.tracer.Start(ctx, "test-path-span")

	span.SetAttributes(
		attribute.String("genkit:path", "/{testFlow,t:flow}/{myAction,t:action}"),
		attribute.Bool("genkit:isFailureSource", true),
		attribute.String("genkit:state", "error"),
		attribute.String("genkit:sessionId", "session-123"),
		attribute.String("genkit:threadName", "thread-456"),
	)
	span.SetStatus(codes.Error, "Test error")

	span.End() // This triggers the pipeline

	// Get captured logs
	logOutput := logBuf.String()

	// Verify path telemetry processed the failing span
	assert.Contains(t, logOutput, "Error[")

	// Verify the span was exported
	spans := f.waitAndGetSpans()
	assert.Len(t, spans, 1)
}

func TestPathTelemetry_MetricCapture(t *testing.T) {
	// Test that verifies we can capture and verify metric calls using OTel's built-in test reader

	testCases := []struct {
		name                   string
		attrs                  map[string]interface{}
		spanStatus             codes.Code
		expectCounterMetrics   bool
		expectHistogramMetrics bool
		expectedFeatureName    string
		expectedError          string
	}{
		{
			name: "failing span captures metrics correctly",
			attrs: map[string]interface{}{
				"genkit:path":            "/{chatFlow,t:flow}/{generateResponse,t:action}",
				"genkit:isFailureSource": true,
				"genkit:state":           "error",
				"genkit:sessionId":       "session-123",
				"genkit:threadName":      "thread-456",
			},
			spanStatus:             codes.Error,
			expectCounterMetrics:   true,
			expectHistogramMetrics: true,
			expectedFeatureName:    "chatFlow",
			expectedError:          "Test error",
		},
		{
			name: "non-failure-source span captures no metrics",
			attrs: map[string]interface{}{
				"genkit:path":            "/{testFlow,t:flow}/{myAction,t:action}",
				"genkit:isFailureSource": false,
				"genkit:state":           "error",
			},
			spanStatus:             codes.Error,
			expectCounterMetrics:   false,
			expectHistogramMetrics: false,
		},
		{
			name: "success span captures no metrics",
			attrs: map[string]interface{}{
				"genkit:path":            "/{testFlow,t:flow}/{myAction,t:action}",
				"genkit:isFailureSource": true,
				"genkit:state":           "success",
			},
			spanStatus:             codes.Ok,
			expectCounterMetrics:   false,
			expectHistogramMetrics: false,
		},
		{
			name: "span without path captures no metrics",
			attrs: map[string]interface{}{
				"genkit:isFailureSource": true,
				"genkit:state":           "error",
			},
			spanStatus:             codes.Error,
			expectCounterMetrics:   false,
			expectHistogramMetrics: false,
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

			// Create path telemetry (it will use the global meter provider)
			pathTel := NewPathTelemetry()
			f := newTestFixture(t, pathTel)

			f.mockExporter.Reset()

			// Create span using the TracerProvider - this will flow through path telemetry
			ctx := context.Background()
			_, span := f.tracer.Start(ctx, "test-path-span")

			for key, value := range tc.attrs {
				switch v := value.(type) {
				case string:
					span.SetAttributes(attribute.String(key, v))
				case bool:
					span.SetAttributes(attribute.Bool(key, v))
				case int:
					span.SetAttributes(attribute.Int(key, v))
				case int64:
					span.SetAttributes(attribute.Int64(key, v))
				case float64:
					span.SetAttributes(attribute.Float64(key, v))
				}
			}

			span.SetStatus(tc.spanStatus, "Test error")
			span.End() // This triggers the pipeline including path telemetry

			// Wait for span to be processed
			spans := f.waitAndGetSpans()
			assert.Len(t, spans, 1)

			// Collect metrics using the manual reader
			var resourceMetrics metricdata.ResourceMetrics
			err := reader.Collect(ctx, &resourceMetrics)
			assert.NoError(t, err)

			// Verify counter metrics
			if tc.expectCounterMetrics {
				counterMetric := findMetric(&resourceMetrics, "genkit/feature/path/requests")
				assert.NotNil(t, counterMetric, "Expected counter metric to be recorded")
				if counterMetric != nil {
					expectedAttrs := map[string]interface{}{
						"featureName": tc.expectedFeatureName,
						"status":      "failure",
						"source":      "genkit-go",
					}
					if tc.expectedError != "" {
						expectedAttrs["error"] = tc.expectedError
					}
					verifyCounterMetric(t, counterMetric, expectedAttrs)
				}
			}

			// Verify histogram metrics
			if tc.expectHistogramMetrics {
				histogramMetric := findMetric(&resourceMetrics, "genkit/feature/path/latency")
				assert.NotNil(t, histogramMetric, "Expected histogram metric to be recorded")
				if histogramMetric != nil {
					expectedAttrs := map[string]interface{}{
						"featureName": tc.expectedFeatureName,
						"status":      "failure",
						"source":      "genkit-go",
					}
					if tc.expectedError != "" {
						expectedAttrs["error"] = tc.expectedError
					}
					verifyHistogramMetric(t, histogramMetric, expectedAttrs)
				}
			}

			if !tc.expectCounterMetrics && !tc.expectHistogramMetrics {
				// Should have no path metrics
				counterMetric := findMetric(&resourceMetrics, "genkit/feature/path/requests")
				histogramMetric := findMetric(&resourceMetrics, "genkit/feature/path/latency")
				assert.Nil(t, counterMetric, "Should not have counter metrics")
				assert.Nil(t, histogramMetric, "Should not have histogram metrics")
			}
		})
	}
}

func TestPathTelemetry_ComprehensiveScenarios(t *testing.T) {
	// Test multiple path telemetry scenarios using the proper pipeline integration

	pathTel := NewPathTelemetry()
	f := newTestFixture(t, pathTel)

	testCases := []struct {
		name         string
		attrs        map[string]interface{}
		spanStatus   codes.Code
		expectLog    bool
		expectedText string
	}{
		{
			name: "failing span with failure source",
			attrs: map[string]interface{}{
				"genkit:path":            "/{chatFlow,t:flow}/{generateResponse,t:action}",
				"genkit:isFailureSource": true,
				"genkit:state":           "error",
				"genkit:sessionId":       "session-123",
				"genkit:threadName":      "thread-456",
			},
			spanStatus:   codes.Error,
			expectLog:    true,
			expectedText: "Error[",
		},
		{
			name: "failing span without failure source",
			attrs: map[string]interface{}{
				"genkit:path":            "/{testFlow,t:flow}/{myAction,t:action}",
				"genkit:isFailureSource": false,
				"genkit:state":           "error",
			},
			spanStatus:   codes.Error,
			expectLog:    false,
			expectedText: "",
		},
		{
			name: "success span skipped",
			attrs: map[string]interface{}{
				"genkit:path":            "/{testFlow,t:flow}/{myAction,t:action}",
				"genkit:isFailureSource": true,
				"genkit:state":           "success",
			},
			spanStatus:   codes.Ok,
			expectLog:    false,
			expectedText: "",
		},
		{
			name: "span without path skipped",
			attrs: map[string]interface{}{
				"genkit:isFailureSource": true,
				"genkit:state":           "error",
			},
			spanStatus:   codes.Error,
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
			_, span := f.tracer.Start(ctx, "test-path-span")

			for key, value := range tc.attrs {
				switch v := value.(type) {
				case string:
					span.SetAttributes(attribute.String(key, v))
				case bool:
					span.SetAttributes(attribute.Bool(key, v))
				case int:
					span.SetAttributes(attribute.Int(key, v))
				case int64:
					span.SetAttributes(attribute.Int64(key, v))
				case float64:
					span.SetAttributes(attribute.Float64(key, v))
				}
			}

			span.SetStatus(tc.spanStatus, "Test error")
			span.End() // This triggers the pipeline including path telemetry

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
				assert.NotContains(t, logOutput, "Error[", "Should not log errors for non-qualifying spans")
			}
		})
	}
}

func TestPathTelemetry_LatencyVerification(t *testing.T) {
	// Specific test to verify that latency measurement actually works correctly

	reader := sdkmetric.NewManualReader()
	testMeterProvider := sdkmetric.NewMeterProvider(sdkmetric.WithReader(reader))
	originalProvider := otel.GetMeterProvider()
	otel.SetMeterProvider(testMeterProvider)
	defer otel.SetMeterProvider(originalProvider)

	pathTel := NewPathTelemetry()
	f := newTestFixture(t, pathTel)

	ctx := context.Background()
	_, span := f.tracer.Start(ctx, "latency-test-span")

	span.SetAttributes(
		attribute.String("genkit:path", "/{testFlow,t:flow}/{latencyTest,t:action}"),
		attribute.Bool("genkit:isFailureSource", true),
		attribute.String("genkit:state", "error"),
		attribute.String("genkit:sessionId", "session-123"),
		attribute.String("genkit:threadName", "thread-456"),
	)
	span.SetStatus(codes.Error, "Test latency error")

	// Add a small delay to ensure measurable latency
	time.Sleep(2 * time.Millisecond)

	span.End()

	// Collect metrics
	var resourceMetrics metricdata.ResourceMetrics
	err := reader.Collect(ctx, &resourceMetrics)
	assert.NoError(t, err)

	// Verify latency histogram
	histogramMetric := findMetric(&resourceMetrics, "genkit/feature/path/latency")
	assert.NotNil(t, histogramMetric, "Expected latency histogram metric")

	if histogramMetric != nil {
		histogram, ok := histogramMetric.Data.(metricdata.Histogram[float64])
		assert.True(t, ok, "Expected histogram type")

		if len(histogram.DataPoints) > 0 {
			dp := histogram.DataPoints[0]

			// More specific latency assertions
			assert.Equal(t, uint64(1), dp.Count, "Should have one measurement")
			assert.GreaterOrEqual(t, dp.Sum, 2.0, "Should have at least 2ms latency due to sleep")
			assert.Less(t, dp.Sum, 100.0, "Should be less than 100ms for test span")

			// Verify histogram has reasonable structure
			assert.NotEmpty(t, dp.BucketCounts, "Should have histogram buckets")
			assert.NotEmpty(t, dp.Bounds, "Should have bucket boundaries")

			// At least one bucket should contain our measurement
			hasNonZeroBucket := false
			for _, count := range dp.BucketCounts {
				if count > 0 {
					hasNonZeroBucket = true
					break
				}
			}
			assert.True(t, hasNonZeroBucket, "At least one bucket should contain the measurement")
		}
	}
}

// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googlecloud

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/metricdata"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// TestFeatureTelemetry_PipelineIntegration verifies that feature telemetry
// processes root spans correctly in the full pipeline
func TestFeatureTelemetry_PipelineIntegration(t *testing.T) {
	// This test verifies that feature telemetry works correctly in the full pipeline,
	// only processing root spans

	featureTel := NewFeatureTelemetry()
	f := newTestFixture(t, featureTel)

	// Set up log capture
	logBuf := setupLogCapture(t)

	// Create span using the TracerProvider - this triggers the full pipeline
	ctx := context.Background()
	_, span := f.tracer.Start(ctx, "test-feature-span")

	span.SetAttributes(
		attribute.Bool("genkit:isRoot", true),
		attribute.String("genkit:name", "testFeature"),
		attribute.String("genkit:path", "/{testFlow,t:flow}/{testFeature,t:action}"),
		attribute.String("genkit:state", "success"),
	)

	span.End() // This triggers the pipeline

	// Get captured logs
	logOutput := logBuf.String()

	// Verify feature telemetry worked - should see debug logs
	assert.Contains(t, logOutput, "FeatureTelemetry.Tick: Processing root span as feature!")

	// Verify the span was exported
	spans := f.waitAndGetSpans()
	assert.Len(t, spans, 1)
}

func TestFeatureTelemetry_MetricCapture(t *testing.T) {
	// Test that verifies we can capture and verify metric calls using OTel's built-in test reader

	testCases := []struct {
		name                   string
		attrs                  map[string]interface{}
		expectCounterMetrics   bool
		expectHistogramMetrics bool
		expectedStatus         string
		expectedError          string
		expectedName           string
	}{
		{
			name: "successful feature captures metrics correctly",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "chatFlow",
				"genkit:path":   "/{chatFlow,t:flow}/{generateResponse,t:action}",
				"genkit:state":  "success",
			},
			expectCounterMetrics:   true,
			expectHistogramMetrics: true,
			expectedStatus:         "success",
			expectedName:           "chatFlow",
		},
		{
			name: "failed feature captures metrics correctly",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "codeAssistant",
				"genkit:path":   "/{codeAssistant,t:flow}/{suggestCode,t:action}",
				"genkit:state":  "error",
			},
			expectCounterMetrics:   true,
			expectHistogramMetrics: true,
			expectedStatus:         "failure",
			expectedName:           "codeAssistant",
			expectedError:          "<unknown>",
		},
		{
			name: "non-root span captures no metrics",
			attrs: map[string]interface{}{
				"genkit:isRoot": false,
				"genkit:name":   "subAction",
				"genkit:state":  "success",
			},
			expectCounterMetrics:   false,
			expectHistogramMetrics: false,
		},
		{
			name: "unknown state captures no metrics",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "testFeature",
				"genkit:state":  "unknown",
			},
			expectCounterMetrics:   false,
			expectHistogramMetrics: false,
		},
		{
			name: "empty string state captures no metrics",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "testFeature",
				"genkit:state":  "", // Explicit empty string
			},
			expectCounterMetrics:   false,
			expectHistogramMetrics: false,
		},
		{
			name: "missing state attribute captures no metrics",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "testFeature",
				// No genkit:state attribute at all
			},
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

			// Create feature telemetry (it will use the global meter provider)
			featureTel := NewFeatureTelemetry()
			f := newTestFixture(t, featureTel)

			f.mockExporter.Reset()

			// Create span using the TracerProvider - this will flow through feature telemetry
			ctx := context.Background()
			_, span := f.tracer.Start(ctx, "test-feature-span")

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

			span.End() // This triggers the pipeline including feature telemetry

			// Wait for span to be processed
			spans := f.waitAndGetSpans()
			assert.Len(t, spans, 1)

			// Collect metrics using the manual reader
			var resourceMetrics metricdata.ResourceMetrics
			err := reader.Collect(ctx, &resourceMetrics)
			assert.NoError(t, err)

			// Verify counter metrics
			if tc.expectCounterMetrics {
				counterMetric := findMetric(&resourceMetrics, "genkit/feature/requests")
				assert.NotNil(t, counterMetric, "Expected counter metric to be recorded")
				if counterMetric != nil {
					expectedAttrs := map[string]interface{}{
						"name":   tc.expectedName,
						"status": tc.expectedStatus,
						"source": "go",
					}
					if tc.expectedError != "" {
						expectedAttrs["error"] = tc.expectedError
					}
					verifyCounterMetric(t, counterMetric, expectedAttrs)
				}
			}

			// Verify histogram metrics
			if tc.expectHistogramMetrics {
				histogramMetric := findMetric(&resourceMetrics, "genkit/feature/latency")
				assert.NotNil(t, histogramMetric, "Expected histogram metric to be recorded")
				if histogramMetric != nil {
					expectedAttrs := map[string]interface{}{
						"name":   tc.expectedName,
						"status": tc.expectedStatus,
						"source": "go",
					}
					if tc.expectedError != "" {
						expectedAttrs["error"] = tc.expectedError
					}
					verifyHistogramMetric(t, histogramMetric, expectedAttrs)
				}
			}

			if !tc.expectCounterMetrics && !tc.expectHistogramMetrics {
				// Should have no feature metrics
				counterMetric := findMetric(&resourceMetrics, "genkit/feature/requests")
				histogramMetric := findMetric(&resourceMetrics, "genkit/feature/latency")
				assert.Nil(t, counterMetric, "Should not have counter metrics")
				assert.Nil(t, histogramMetric, "Should not have histogram metrics")
			}
		})
	}
}

func TestFeatureTelemetry_ComprehensiveScenarios(t *testing.T) {
	// Test multiple feature telemetry scenarios using the proper pipeline integration

	featureTel := NewFeatureTelemetry()
	f := newTestFixture(t, featureTel)

	testCases := []struct {
		name         string
		attrs        map[string]interface{}
		expectLog    bool
		expectedText string
	}{
		{
			name: "successful root span",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "chatFlow",
				"genkit:path":   "/{chatFlow,t:flow}/{generateResponse,t:action}",
				"genkit:state":  "success",
			},
			expectLog:    true,
			expectedText: "FeatureTelemetry.Tick: Processing root span as feature!",
		},
		{
			name: "failed root span",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "codeAssistant",
				"genkit:path":   "/{codeAssistant,t:flow}/{suggestCode,t:action}",
				"genkit:state":  "error",
			},
			expectLog:    true,
			expectedText: "FeatureTelemetry.Tick: Processing root span as feature!",
		},
		{
			name: "non-root span skipped",
			attrs: map[string]interface{}{
				"genkit:isRoot": false,
				"genkit:name":   "subAction",
				"genkit:state":  "success",
			},
			expectLog:    true,
			expectedText: "FeatureTelemetry.Tick: Skipping non-root span",
		},
		{
			name: "unknown state",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "testFeature",
				"genkit:state":  "unknown",
			},
			expectLog:    true,
			expectedText: "Unknown feature state",
		},
		{
			name: "missing state attribute",
			attrs: map[string]interface{}{
				"genkit:isRoot": true,
				"genkit:name":   "testFeature",
			},
			expectLog:    true,
			expectedText: "Unknown feature state",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			f.mockExporter.Reset()

			// Set up log capture
			logBuf := setupLogCapture(t)

			// Create span using the TracerProvider - this triggers the full pipeline
			ctx := context.Background()
			_, span := f.tracer.Start(ctx, "test-feature-span")

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

			span.End() // This triggers the pipeline including feature telemetry

			// Get captured logs
			logOutput := logBuf.String()

			// Verify spans were processed
			spans := f.waitAndGetSpans()
			assert.Len(t, spans, 1)

			// Check logging behavior
			if tc.expectLog {
				assert.Contains(t, logOutput, tc.expectedText,
					"Expected log containing %q but got: %q", tc.expectedText, logOutput)
			}
		})
	}
}

func TestFeatureTelemetry_InputOutputLogging(t *testing.T) {
	// Test that input/output logging works when logInputOutput is enabled

	featureTel := NewFeatureTelemetry()

	// Create custom fixture with logInputOutput enabled
	mockExporter := NewTestSpanExporter()
	adjuster := &AdjustingTraceExporter{
		exporter:          mockExporter,
		modules:           []Telemetry{featureTel},
		logInputAndOutput: true, // Enable input/output logging for this test
		projectId:         "test-project",
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithSpanProcessor(sdktrace.NewSimpleSpanProcessor(adjuster)),
	)
	defer tp.Shutdown(context.Background())

	f := &testFixture{
		mockExporter: mockExporter,
		adjuster:     adjuster,
		tracer:       tp.Tracer("test-tracer"),
		tp:           tp,
		ctx:          context.Background(),
	}

	// Set up log capture
	logBuf := setupLogCapture(t)

	// Create span with input/output data
	ctx := context.Background()
	_, span := f.tracer.Start(ctx, "test-feature-span")

	span.SetAttributes(
		attribute.Bool("genkit:isRoot", true),
		attribute.String("genkit:name", "testFeature"),
		attribute.String("genkit:path", "/{testFlow,t:flow}/{testFeature,t:action}"),
		attribute.String("genkit:state", "success"),
		attribute.String("genkit:input", `{"prompt": "Hello world"}`),
		attribute.String("genkit:output", `{"response": "Hi there!"}`),
		attribute.String("genkit:sessionId", "session-123"),
		attribute.String("genkit:threadName", "thread-456"),
	)

	span.End() // This triggers the pipeline

	// Get captured logs
	logOutput := logBuf.String()

	// Verify input/output logs are present - we explicitly enabled logInputOutput=true
	assert.Contains(t, logOutput, "Input[", "Expected input log")
	assert.Contains(t, logOutput, "Output[", "Expected output log")
	assert.Contains(t, logOutput, "testFeature", "Expected feature name in logs")

	// Verify spans were processed
	spans := f.waitAndGetSpans()
	assert.Len(t, spans, 1)
}

// Helper function for histogram metric verification (reuses counter verification pattern)
func verifyHistogramMetric(t *testing.T, metric *metricdata.Metrics, expectedAttrs map[string]interface{}) {
	// Verify it's a histogram metric
	histogram, ok := metric.Data.(metricdata.Histogram[float64])
	assert.True(t, ok, "Expected metric to be a Histogram[float64]")

	// Should have exactly one data point for our test
	assert.Len(t, histogram.DataPoints, 1, "Expected exactly one data point")

	if len(histogram.DataPoints) > 0 {
		dp := histogram.DataPoints[0]

		// Verify the count (should be 1 for our test)
		assert.Equal(t, uint64(1), dp.Count, "Expected histogram count to be 1")

		// Verify the latency value is reasonable for a test span
		assert.Greater(t, dp.Sum, float64(0), "Expected histogram sum to be positive")

		// Verify we have bucket counts (histogram should have buckets)
		assert.NotEmpty(t, dp.BucketCounts, "Expected histogram to have bucket counts")

		// Verify the sum of bucket counts equals the total count
		var totalBucketCount uint64
		for _, bucketCount := range dp.BucketCounts {
			totalBucketCount += bucketCount
		}
		assert.Equal(t, dp.Count, totalBucketCount, "Sum of bucket counts should equal total count")

		// Verify attributes (reuse same pattern as counter verification)
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

func TestFeatureTelemetry_LatencyVerification(t *testing.T) {
	// Specific test to verify that latency measurement actually works correctly

	reader := sdkmetric.NewManualReader()
	testMeterProvider := sdkmetric.NewMeterProvider(sdkmetric.WithReader(reader))
	originalProvider := otel.GetMeterProvider()
	otel.SetMeterProvider(testMeterProvider)
	defer otel.SetMeterProvider(originalProvider)

	featureTel := NewFeatureTelemetry()
	f := newTestFixture(t, featureTel)

	ctx := context.Background()
	_, span := f.tracer.Start(ctx, "latency-test-span")

	span.SetAttributes(
		attribute.Bool("genkit:isRoot", true),
		attribute.String("genkit:name", "latencyTestFeature"),
		attribute.String("genkit:state", "success"),
	)

	// Add a small delay to ensure measurable latency
	time.Sleep(1 * time.Millisecond)

	span.End()

	// Collect metrics
	var resourceMetrics metricdata.ResourceMetrics
	err := reader.Collect(ctx, &resourceMetrics)
	assert.NoError(t, err)

	// Verify latency histogram
	histogramMetric := findMetric(&resourceMetrics, "genkit/feature/latency")
	assert.NotNil(t, histogramMetric, "Expected latency histogram metric")

	if histogramMetric != nil {
		histogram, ok := histogramMetric.Data.(metricdata.Histogram[float64])
		assert.True(t, ok, "Expected histogram type")

		if len(histogram.DataPoints) > 0 {
			dp := histogram.DataPoints[0]

			// More specific latency assertions
			assert.Equal(t, uint64(1), dp.Count, "Should have one measurement")
			assert.GreaterOrEqual(t, dp.Sum, 1.0, "Should have at least 1ms latency due to sleep")
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

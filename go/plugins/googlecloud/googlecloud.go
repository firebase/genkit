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

// The googlecloud package supports telemetry (tracing, metrics and logging) using
// Google Cloud services.
package googlecloud

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strings"
	"time"

	"cloud.google.com/go/logging"
	mexporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/metric"
	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"go.opentelemetry.io/contrib/detectors/gcp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

const provider = "googlecloud"

// NewWithConfig creates a new GoogleCloud plugin with a pre-configured TelemetryConfig.
// This is useful when you want to pass configuration as a struct instead of functional options.
func NewWithConfig(projectID string, telemetryConfig *TelemetryConfig) *GoogleCloud {
	config := &PluginConfig{
		ProjectID:   projectID,
		Credentials: nil, // Will be auto-detected
		Config:      telemetryConfig,
	}

	return &GoogleCloud{Config: config}
}

// EnableGoogleCloudTelemetry creates a Google Cloud telemetry plugin with simple struct-based configuration.
func EnableGoogleCloudTelemetry(options ...*GoogleCloudTelemetryOptions) *GoogleCloud {
	var opts *GoogleCloudTelemetryOptions
	if len(options) > 0 && options[0] != nil {
		opts = options[0]
	} else {
		opts = &GoogleCloudTelemetryOptions{}
	}

	// Auto-detect project ID if not provided
	projectID := opts.ProjectID
	if projectID == "" {
		if envProjectID := os.Getenv("GOOGLE_CLOUD_PROJECT"); envProjectID != "" {
			projectID = envProjectID
		}
	}

	// Build simplified configuration
	config := &TelemetryConfig{
		ForceExport:          opts.ForceExport,
		ExportInputAndOutput: opts.ExportInputAndOutput,
		LogLevel:             slog.LevelInfo,
	}

	// Set environment-aware performance defaults
	if IsDevEnv() {
		config.MetricInterval = 5 * time.Second
		config.MetricTimeoutMillis = 5000
		config.BufferSize = 100
		config.Export = opts.ForceExport // Only export in dev if forced
	} else {
		config.MetricInterval = 300 * time.Second
		config.MetricTimeoutMillis = 300000
		config.BufferSize = 1000
		config.Export = true // Always export in production
	}

	return NewWithConfig(projectID, config)
}

// GoogleCloud is a Genkit plugin for comprehensive telemetry using Google Cloud services.
type GoogleCloud struct {
	Config   *PluginConfig
	modules  []Telemetry
	resource *resource.Resource
}

// Name returns the name of the plugin.
func (gc *GoogleCloud) Name() string {
	return provider
}

// setupModules creates and registers all telemetry modules for comprehensive observability
func (gc *GoogleCloud) setupModules() {
	// All modules are enabled by default for comprehensive observability
	// This matches the JavaScript approach of opinionated defaults
	gc.modules = []Telemetry{
		NewGenerateTelemetry(),
		NewFeatureTelemetry(),
		NewActionTelemetry(),
		NewEngagementTelemetry(),
		NewPathTelemetry(),
	}

	slog.Debug("Enabled all telemetry modules for comprehensive observability")

	slog.Info("Telemetry modules initialized", "modules", len(gc.modules))
}

// detectResource auto-detects GCP resource information
func (gc *GoogleCloud) detectResource(ctx context.Context) error {
	// Start with a base resource
	baseResource := resource.NewWithAttributes(
		semconv.SchemaURL,
		semconv.ServiceName("genkit"),
		semconv.ServiceVersion(internal.Version), // Use actual Genkit version
	)

	// Auto-detect GCP environment (GCE, GKE, Cloud Functions, App Engine, etc.)
	detector := gcp.NewDetector()
	detectedResource, err := detector.Detect(ctx)
	if err != nil {
		// Use base resource as fallback
		gc.resource = baseResource
		return fmt.Errorf("GCP resource detection failed, using default: %w", err)
	}

	// Merge base resource with detected GCP resource
	gc.resource, err = resource.Merge(baseResource, detectedResource)
	if err != nil {
		gc.resource = baseResource
		return fmt.Errorf("failed to merge resources, using default: %w", err)
	}

	// Log detected resource information for debugging
	attrs := gc.resource.Attributes()
	slog.Info("Detected GCP resource", "attributes", attrs)

	return nil
}

// getCredentialHelpText returns helpful error message for credential configuration
func getCredentialHelpText() string {
	return `To configure Google Cloud credentials, you can:

1. Set the GCLOUD_SERVICE_ACCOUNT_CREDS environment variable:
   export GCLOUD_SERVICE_ACCOUNT_CREDS='{"type":"service_account",...}'

2. Use Application Default Credentials (ADC):
   gcloud auth application-default login

3. Set the GOOGLE_APPLICATION_CREDENTIALS environment variable:
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

4. On Google Cloud Platform, credentials are automatically detected.

For more information, see: https://cloud.google.com/docs/authentication/getting-started`
}

// Init initializes comprehensive telemetry using Google Cloud services.
// Uses environment-aware defaults (dev vs prod) for optimal configuration.
// In the dev environment, this does nothing unless [ForceExport] is true.
func (gc *GoogleCloud) Init(ctx context.Context, g *genkit.Genkit) (err error) {
	defer func() {
		if err != nil {
			err = fmt.Errorf("googlecloud.Init: %w", err)
		}
	}()

	if gc.Config.ProjectID == "" {
		return fmt.Errorf("config missing ProjectID")
	}

	shouldExport := gc.Config.Config.ForceExport || os.Getenv("GENKIT_ENV") != "dev"
	if !shouldExport {
		return nil
	}

	// Auto-detect GCP resource information
	if err := gc.detectResource(ctx); err != nil {
		slog.Warn("Failed to detect GCP resource, using default", "error", err)
	}

	// Set up telemetry modules based on configuration
	gc.setupModules()

	// Create the final destination trace exporter
	baseExporter, err := texporter.New(texporter.WithProjectID(gc.Config.ProjectID))
	if err != nil {
		return fmt.Errorf("failed to create trace exporter: %w", err)
	}

	// Create adjusting trace exporter that handles both PII filtering and telemetry processing
	adjustingExporter := &AdjustingTraceExporter{
		exporter:          baseExporter,
		modules:           gc.modules,
		logInputAndOutput: gc.Config.Config.ExportInputAndOutput,
		projectId:         gc.Config.ProjectID,
	}

	// Create span processor with adjusting exporter
	spanProcessor := sdktrace.NewBatchSpanProcessor(adjustingExporter)

	// Register the adjusting span processor
	genkit.RegisterSpanProcessor(g, spanProcessor)

	slog.Info("GoogleCloud plugin initialized with telemetry modules",
		"project_id", gc.Config.ProjectID,
		"modules", len(gc.modules))

	// Set up metrics and logging
	if err := setMeterProvider(gc.Config.ProjectID, gc.Config.Config.MetricInterval); err != nil {
		return err
	}
	return setLogHandler(gc.Config.ProjectID, gc.Config.Config.LogLevel)
}

func setMeterProvider(projectID string, interval time.Duration) error {
	mexp, err := mexporter.New(mexporter.WithProjectID(projectID))
	if err != nil {
		return fmt.Errorf("failed to create metrics exporter: %w", err)
	}
	r := sdkmetric.NewPeriodicReader(mexp, sdkmetric.WithInterval(interval))
	mp := sdkmetric.NewMeterProvider(sdkmetric.WithReader(r))
	otel.SetMeterProvider(mp)
	return nil
}

func setLogHandler(projectID string, level slog.Leveler) error {
	c, err := logging.NewClient(context.Background(), "projects/"+projectID)
	if err != nil {
		return fmt.Errorf("failed to create logging client: %w", err)
	}
	logger := c.Logger("genkit_log")
	slog.SetDefault(slog.New(newHandler(level, logger.Log, projectID)))
	return nil
}

// AdjustingTraceExporter combines PII filtering and telemetry processing
type AdjustingTraceExporter struct {
	exporter          sdktrace.SpanExporter
	modules           []Telemetry
	logInputAndOutput bool
	projectId         string
	spansProcessed    int64
}

func (e *AdjustingTraceExporter) ExportSpans(ctx context.Context, spans []sdktrace.ReadOnlySpan) error {
	slog.Debug("Processing span batch", "span_count", len(spans), "modules_count", len(e.modules))

	// Process and adjust spans (both telemetry and PII filtering)
	adjustedSpans := e.adjust(spans)

	slog.Debug("Span batch processed", "spans_processed_total", e.spansProcessed)

	// Forward adjusted spans to base exporter
	return e.exporter.ExportSpans(ctx, adjustedSpans)
}

func (e *AdjustingTraceExporter) Shutdown(ctx context.Context) error {
	slog.Info("Shutting down adjusting trace exporter", "spans_processed", e.spansProcessed)
	return e.exporter.Shutdown(ctx)
}

func (e *AdjustingTraceExporter) ForceFlush(ctx context.Context) error {
	if flusher, ok := e.exporter.(interface{ ForceFlush(context.Context) error }); ok {
		return flusher.ForceFlush(ctx)
	}
	return nil
}

func (e *AdjustingTraceExporter) adjust(spans []sdktrace.ReadOnlySpan) []sdktrace.ReadOnlySpan {
	var adjustedSpans []sdktrace.ReadOnlySpan

	for _, span := range spans {
		// Process telemetry first
		e.tickTelemetry(span)
		e.spansProcessed++

		// Apply all span transformations
		adjustedSpan := span
		adjustedSpan = e.redactInputOutput(adjustedSpan)
		adjustedSpan = e.markErrorSpanAsError(adjustedSpan)
		adjustedSpan = e.markFailedSpan(adjustedSpan)
		adjustedSpan = e.markGenkitFeature(adjustedSpan)
		adjustedSpan = e.markGenkitModel(adjustedSpan)
		adjustedSpan = e.setRootState(adjustedSpan)
		adjustedSpan = e.normalizeLabels(adjustedSpan)

		adjustedSpans = append(adjustedSpans, adjustedSpan)
	}

	return adjustedSpans
}

// tickTelemetry processes telemetry for each span using all configured modules
func (e *AdjustingTraceExporter) tickTelemetry(span sdktrace.ReadOnlySpan) {
	if len(e.modules) == 0 {
		return
	}

	// Process through all enabled modules
	for _, module := range e.modules {
		if module != nil {
			module.Tick(span, e.logInputAndOutput, e.projectId)
		}
	}
}

// redactInputOutput applies PII filtering
func (e *AdjustingTraceExporter) redactInputOutput(span sdktrace.ReadOnlySpan) sdktrace.ReadOnlySpan {
	hasInput := false
	hasOutput := false

	// Check if span has input/output attributes
	for _, attr := range span.Attributes() {
		if attr.Key == "genkit:input" {
			hasInput = true
		}
		if attr.Key == "genkit:output" {
			hasOutput = true
		}
	}

	if !hasInput && !hasOutput {
		return span
	}

	return &spanWithModifiedAttributes{
		ReadOnlySpan: span,
		modifyFunc: func(attrs []attribute.KeyValue) []attribute.KeyValue {
			var newAttrs []attribute.KeyValue
			for _, attr := range attrs {
				if attr.Key == "genkit:input" {
					newAttrs = append(newAttrs, attribute.String("genkit:input", "<redacted>"))
				} else if attr.Key == "genkit:output" {
					newAttrs = append(newAttrs, attribute.String("genkit:output", "<redacted>"))
				} else {
					newAttrs = append(newAttrs, attr)
				}
			}
			return newAttrs
		},
	}
}

// markErrorSpanAsError adds error marking for GCP Trace
func (e *AdjustingTraceExporter) markErrorSpanAsError(span sdktrace.ReadOnlySpan) sdktrace.ReadOnlySpan {
	if span.Status().Code != codes.Error {
		return span
	}

	return &spanWithModifiedAttributes{
		ReadOnlySpan: span,
		modifyFunc: func(attrs []attribute.KeyValue) []attribute.KeyValue {
			newAttrs := make([]attribute.KeyValue, len(attrs))
			copy(newAttrs, attrs)
			newAttrs = append(newAttrs, attribute.String("/http/status_code", "599"))
			return newAttrs
		},
	}
}

// markFailedSpan marks spans that are failure sources
func (e *AdjustingTraceExporter) markFailedSpan(span sdktrace.ReadOnlySpan) sdktrace.ReadOnlySpan {
	var isFailureSource bool
	var name, path string

	for _, attr := range span.Attributes() {
		if attr.Key == "genkit:isFailureSource" {
			isFailureSource = attr.Value.AsBool()
		}
		if attr.Key == "genkit:name" {
			name = attr.Value.AsString()
		}
		if attr.Key == "genkit:path" {
			path = attr.Value.AsString()
		}
	}

	if !isFailureSource {
		return span
	}

	return &spanWithModifiedAttributes{
		ReadOnlySpan: span,
		modifyFunc: func(attrs []attribute.KeyValue) []attribute.KeyValue {
			newAttrs := make([]attribute.KeyValue, len(attrs))
			copy(newAttrs, attrs)
			newAttrs = append(newAttrs, attribute.String("genkit:failedSpan", name))
			newAttrs = append(newAttrs, attribute.String("genkit:failedPath", path))
			return newAttrs
		},
	}
}

// markGenkitFeature marks root spans with feature name
func (e *AdjustingTraceExporter) markGenkitFeature(span sdktrace.ReadOnlySpan) sdktrace.ReadOnlySpan {
	var isRoot bool
	var name string

	for _, attr := range span.Attributes() {
		if attr.Key == "genkit:isRoot" {
			isRoot = attr.Value.AsBool()
		}
		if attr.Key == "genkit:name" {
			name = attr.Value.AsString()
		}
	}

	if !isRoot || name == "" {
		return span
	}

	return &spanWithModifiedAttributes{
		ReadOnlySpan: span,
		modifyFunc: func(attrs []attribute.KeyValue) []attribute.KeyValue {
			newAttrs := make([]attribute.KeyValue, len(attrs))
			copy(newAttrs, attrs)
			newAttrs = append(newAttrs, attribute.String("genkit:feature", name))
			return newAttrs
		},
	}
}

// markGenkitModel marks model spans with model name
func (e *AdjustingTraceExporter) markGenkitModel(span sdktrace.ReadOnlySpan) sdktrace.ReadOnlySpan {
	var subtype, name string

	for _, attr := range span.Attributes() {
		if attr.Key == "genkit:metadata:subtype" {
			subtype = attr.Value.AsString()
		}
		if attr.Key == "genkit:name" {
			name = attr.Value.AsString()
		}
	}

	if subtype != "model" || name == "" {
		return span
	}

	return &spanWithModifiedAttributes{
		ReadOnlySpan: span,
		modifyFunc: func(attrs []attribute.KeyValue) []attribute.KeyValue {
			newAttrs := make([]attribute.KeyValue, len(attrs))
			copy(newAttrs, attrs)
			newAttrs = append(newAttrs, attribute.String("genkit:model", name))
			return newAttrs
		},
	}
}

// normalizeLabels converts attribute keys from : to /
func (e *AdjustingTraceExporter) normalizeLabels(span sdktrace.ReadOnlySpan) sdktrace.ReadOnlySpan {
	return &spanWithModifiedAttributes{
		ReadOnlySpan: span,
		modifyFunc: func(attrs []attribute.KeyValue) []attribute.KeyValue {
			newAttrs := make([]attribute.KeyValue, len(attrs))
			for i, attr := range attrs {
				newKey := strings.ReplaceAll(string(attr.Key), ":", "/")
				newAttrs[i] = attribute.KeyValue{
					Key:   attribute.Key(newKey),
					Value: attr.Value,
				}
			}
			return newAttrs
		},
	}
}

// setRootState copies genkit:state to genkit:rootState for root spans
func (e *AdjustingTraceExporter) setRootState(span sdktrace.ReadOnlySpan) sdktrace.ReadOnlySpan {
	var isRoot bool
	var state string

	for _, attr := range span.Attributes() {
		if attr.Key == "genkit:isRoot" {
			isRoot = attr.Value.AsBool()
		}
		if attr.Key == "genkit:state" {
			state = attr.Value.AsString()
		}
	}

	if !isRoot || state == "" {
		return span
	}

	return &spanWithModifiedAttributes{
		ReadOnlySpan: span,
		modifyFunc: func(attrs []attribute.KeyValue) []attribute.KeyValue {
			newAttrs := make([]attribute.KeyValue, len(attrs))
			copy(newAttrs, attrs)
			newAttrs = append(newAttrs, attribute.String("genkit:rootState", state))
			return newAttrs
		},
	}
}

// spanWithModifiedAttributes wraps a span and modifies its attributes
type spanWithModifiedAttributes struct {
	sdktrace.ReadOnlySpan
	modifyFunc func([]attribute.KeyValue) []attribute.KeyValue
}

func (s *spanWithModifiedAttributes) Attributes() []attribute.KeyValue {
	return s.modifyFunc(s.ReadOnlySpan.Attributes())
}

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
	"fmt"
	"log/slog"
	"os"
	"time"

	mexporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/metric"
	texporter "github.com/GoogleCloudPlatform/opentelemetry-operations-go/exporter/trace"
	"github.com/firebase/genkit/go/genkit"
	"go.opentelemetry.io/otel"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// TelemetryConfig represents configuration options for telemetry setup
type TelemetryConfig struct {
	// Core settings
	ProjectID   string
	ForceExport bool

	// Module selection
	EnableGenerate   bool // Enable model interaction telemetry
	EnableFeature    bool // Enable top-level feature telemetry
	EnableAction     bool // Enable action input/output logging
	EnableEngagement bool // Enable user engagement tracking
	EnablePath       bool // Enable error/failure path tracking

	// Logging settings
	LogInputOutput bool
	LogLevel       slog.Level

	// Performance settings
	MetricInterval      time.Duration
	MetricTimeoutMillis int
	BufferSize          int
}

// DefaultTelemetryConfig returns a configuration with sensible defaults
func DefaultTelemetryConfig() *TelemetryConfig {
	return &TelemetryConfig{
		// Core settings
		ForceExport: false,

		// Enable all modules by default
		EnableGenerate:   true,
		EnableFeature:    true,
		EnableAction:     true,
		EnableEngagement: true,
		EnablePath:       true,

		// Logging settings
		LogInputOutput: true,
		LogLevel:       slog.LevelInfo,

		// Performance settings
		MetricInterval:      60 * time.Second,
		MetricTimeoutMillis: 60000,
		BufferSize:          1000,
	}
}

// TelemetryManager manages all telemetry modules and provides easy configuration
type TelemetryManager struct {
	config   *TelemetryConfig
	modules  []Telemetry
	exporter *enhancedTraceExporter
}

// NewTelemetryManager creates a new telemetry manager with the specified configuration
func NewTelemetryManager(config *TelemetryConfig) *TelemetryManager {
	if config == nil {
		config = DefaultTelemetryConfig()
	}

	manager := &TelemetryManager{
		config:  config,
		modules: make([]Telemetry, 0, 5),
	}

	// Auto-create enabled modules
	manager.setupModules()

	return manager
}

// setupModules automatically creates and registers enabled telemetry modules
func (tm *TelemetryManager) setupModules() {
	if tm.config.EnableGenerate {
		tm.modules = append(tm.modules, NewGenerateTelemetry())
		slog.Debug("Enabled generate telemetry module")
	}

	if tm.config.EnableFeature {
		tm.modules = append(tm.modules, NewFeatureTelemetry())
		slog.Debug("Enabled feature telemetry module")
	}

	if tm.config.EnableAction {
		tm.modules = append(tm.modules, NewActionTelemetry())
		slog.Debug("Enabled action telemetry module")
	}

	if tm.config.EnableEngagement {
		tm.modules = append(tm.modules, NewEngagementTelemetry())
		slog.Debug("Enabled engagement telemetry module")
	}

	if tm.config.EnablePath {
		tm.modules = append(tm.modules, NewPathTelemetry())
		slog.Debug("Enabled path telemetry module")
	}

	slog.Info("Telemetry manager initialized", "modules", len(tm.modules))
}

// GetModules returns all configured telemetry modules
func (tm *TelemetryManager) GetModules() []Telemetry {
	return tm.modules
}

// CreateEnhancedExporter creates an enhanced trace exporter with all configured modules
func (tm *TelemetryManager) CreateEnhancedExporter(baseExporter sdktrace.SpanExporter) sdktrace.SpanProcessor {
	tm.exporter = &enhancedTraceExporter{
		baseExporter:   baseExporter,
		modules:        tm.modules,
		logInputOutput: tm.config.LogInputOutput,
		projectID:      tm.config.ProjectID,
		bufferSize:     tm.config.BufferSize,
		spanBuffer:     make([]sdktrace.ReadOnlySpan, 0, tm.config.BufferSize),
	}

	return sdktrace.NewBatchSpanProcessor(tm.exporter)
}

// AddModule adds a custom telemetry module to the manager
func (tm *TelemetryManager) AddModule(module Telemetry) {
	tm.modules = append(tm.modules, module)
	slog.Debug("Added custom telemetry module", "total_modules", len(tm.modules))
}

// GetConfig returns the current telemetry configuration
func (tm *TelemetryManager) GetConfig() *TelemetryConfig {
	return tm.config
}

// UpdateConfig updates the telemetry configuration (requires restart to take effect)
func (tm *TelemetryManager) UpdateConfig(newConfig *TelemetryConfig) {
	tm.config = newConfig
	tm.modules = tm.modules[:0] // Clear existing modules
	tm.setupModules()           // Re-setup with new config
	slog.Info("Telemetry configuration updated", "modules", len(tm.modules))
}

// GetStats returns telemetry statistics
func (tm *TelemetryManager) GetStats() TelemetryStats {
	stats := TelemetryStats{
		ModulesEnabled: len(tm.modules),
		ModuleNames:    make([]string, 0, len(tm.modules)),
	}

	// Add module type information
	for _, module := range tm.modules {
		switch module.(type) {
		case *GenerateTelemetry:
			stats.ModuleNames = append(stats.ModuleNames, "generate")
		case *FeatureTelemetry:
			stats.ModuleNames = append(stats.ModuleNames, "feature")
		case *ActionTelemetry:
			stats.ModuleNames = append(stats.ModuleNames, "action")
		case *EngagementTelemetry:
			stats.ModuleNames = append(stats.ModuleNames, "engagement")
		case *PathTelemetry:
			stats.ModuleNames = append(stats.ModuleNames, "path")
		default:
			stats.ModuleNames = append(stats.ModuleNames, "custom")
		}
	}

	if tm.exporter != nil {
		stats.SpansProcessed = tm.exporter.getSpansProcessed()
		stats.SpansBuffered = tm.exporter.getSpansBuffered()
	}

	return stats
}

// TelemetryStats provides runtime statistics about telemetry processing
type TelemetryStats struct {
	ModulesEnabled int      `json:"modules_enabled"`
	ModuleNames    []string `json:"module_names"`
	SpansProcessed int64    `json:"spans_processed"`
	SpansBuffered  int      `json:"spans_buffered"`
}

// enhancedTraceExporter is an improved version with better performance and diagnostics
type enhancedTraceExporter struct {
	baseExporter   sdktrace.SpanExporter
	modules        []Telemetry
	logInputOutput bool
	projectID      string
	bufferSize     int
	spanBuffer     []sdktrace.ReadOnlySpan
	spansProcessed int64
}

func (e *enhancedTraceExporter) ExportSpans(ctx context.Context, spans []sdktrace.ReadOnlySpan) error {
	slog.Info("enhancedTraceExporter.ExportSpans: Processing batch",
		"span_count", len(spans),
		"modules_count", len(e.modules))

	// Process telemetry for each span
	for i, span := range spans {
		slog.Info("enhancedTraceExporter.ExportSpans: Processing span",
			"span_index", i,
			"span_name", span.Name(),
			"span_kind", span.SpanKind())
		e.processTelemetryOptimized(span)
		e.spansProcessed++
	}

	slog.Info("enhancedTraceExporter.ExportSpans: Batch completed",
		"spans_processed_total", e.spansProcessed)

	// Forward to base exporter
	return e.baseExporter.ExportSpans(ctx, spans)
}

func (e *enhancedTraceExporter) Shutdown(ctx context.Context) error {
	slog.Info("Shutting down enhanced trace exporter", "spans_processed", e.spansProcessed)
	return e.baseExporter.Shutdown(ctx)
}

func (e *enhancedTraceExporter) ForceFlush(ctx context.Context) error {
	if flusher, ok := e.baseExporter.(interface{ ForceFlush(context.Context) error }); ok {
		return flusher.ForceFlush(ctx)
	}
	return nil
}

// processTelemetryOptimized processes telemetry with performance optimizations
func (e *enhancedTraceExporter) processTelemetryOptimized(span sdktrace.ReadOnlySpan) {
	if len(e.modules) == 0 {
		return
	}

	// Parallel processing for better performance
	for _, module := range e.modules {
		if module != nil {
			// Each module processes independently
			module.Tick(span, e.logInputOutput, e.projectID)
		}
	}
}

func (e *enhancedTraceExporter) getSpansProcessed() int64 {
	return e.spansProcessed
}

func (e *enhancedTraceExporter) getSpansBuffered() int {
	return len(e.spanBuffer)
}

// TelemetryGoogleCloud is an enhanced Google Cloud plugin that integrates with telemetry modules
type TelemetryGoogleCloud struct {
	*GoogleCloud
	manager *TelemetryManager
}

// Init initializes the Google Cloud plugin with telemetry integration
func (tgc *TelemetryGoogleCloud) Init(ctx context.Context, g *genkit.Genkit) error {
	if tgc.GoogleCloud.ProjectID == "" {
		return fmt.Errorf("config missing ProjectID")
	}

	shouldExport := tgc.GoogleCloud.ForceExport || os.Getenv("GENKIT_ENV") != "dev"
	if !shouldExport {
		return nil
	}

	// Create the final destination trace exporter.
	finalExporter, err := texporter.New(texporter.WithProjectID(tgc.GoogleCloud.ProjectID))
	if err != nil {
		return fmt.Errorf("failed to create trace exporter: %w", err)
	}

	// Wrap the final exporter with our PII-filtering security layer.
	piiFilterExporter := &adjustingTraceExporter{finalExporter}

	// Create the enhanced span processor, which runs the telemetry modules
	// and chains to the PII filter.
	enhancedProcessor := tgc.manager.CreateEnhancedExporter(piiFilterExporter)

	// Register the start of the full, correct pipeline.
	genkit.RegisterSpanProcessor(g, enhancedProcessor)

	slog.Info("Enhanced Google Cloud plugin initialized with telemetry integration",
		"project_id", tgc.GoogleCloud.ProjectID,
		"modules", len(tgc.manager.modules))

	// Set up metrics (logging setup is handled separately for now)
	if err := setupMeterProvider(tgc.GoogleCloud.ProjectID, tgc.GoogleCloud.MetricInterval); err != nil {
		return fmt.Errorf("failed to setup MeterProvider: %w", err)
	}

	return nil
}

// SetupWithTelemetryManager is a convenience function to set up Google Cloud plugin with telemetry
func SetupWithTelemetryManager(ctx context.Context, config *TelemetryConfig) (*TelemetryGoogleCloud, *TelemetryManager, error) {
	if config.ProjectID == "" {
		return nil, nil, fmt.Errorf("ProjectID is required")
	}

	// Create telemetry manager
	manager := NewTelemetryManager(config)

	// Create enhanced Google Cloud plugin with telemetry integration
	gc := &GoogleCloud{
		ProjectID:      config.ProjectID,
		ForceExport:    config.ForceExport,
		MetricInterval: config.MetricInterval,
		LogLevel:       config.LogLevel,
	}

	tgc := &TelemetryGoogleCloud{
		GoogleCloud: gc,
		manager:     manager,
	}

	slog.Info("Google Cloud plugin with telemetry created",
		"project_id", config.ProjectID,
		"force_export", config.ForceExport,
		"modules", len(manager.modules))

	return tgc, manager, nil
}

// setupMeterProvider sets up the OpenTelemetry MeterProvider for Google Cloud export
func setupMeterProvider(projectID string, interval time.Duration) error {
	mexp, err := mexporter.New(mexporter.WithProjectID(projectID))
	if err != nil {
		return err
	}
	r := sdkmetric.NewPeriodicReader(mexp, sdkmetric.WithInterval(interval))
	mp := sdkmetric.NewMeterProvider(sdkmetric.WithReader(r))
	otel.SetMeterProvider(mp)
	slog.Info("OpenTelemetry MeterProvider configured for Google Cloud", "project_id", projectID, "interval", interval)
	return nil
}

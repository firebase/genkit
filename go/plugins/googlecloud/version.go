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
	"fmt"
	"runtime/debug"
	"sync"
)

// Version information for the Google Cloud telemetry plugin
const (
	// PluginVersion is the current version of the Go Google Cloud telemetry plugin
	PluginVersion = "1.0.0"

	// PluginName is the canonical name of this plugin
	PluginName = "genkit-go-googlecloud"

	// TelemetrySource identifies this implementation in telemetry data
	TelemetrySource = "go"

	// DefaultProjection is used when project ID cannot be determined
	DefaultProjection = "unknown-project"
)

// Build information populated at build time or runtime
var (
	// buildVersion can be set via ldflags: -X github.com/firebase/genkit/go/plugins/googlecloud.buildVersion=v1.2.3
	buildVersion = ""

	// buildCommit can be set via ldflags: -X github.com/firebase/genkit/go/plugins/googlecloud.buildCommit=abc123
	buildCommit = ""

	// buildTime can be set via ldflags: -X github.com/firebase/genkit/go/plugins/googlecloud.buildTime=2024-01-15T10:30:00Z
	buildTime = ""

	// versionInfo holds cached version information
	versionInfo     *VersionInfo
	versionInfoOnce sync.Once
)

// VersionInfo contains comprehensive version and build information
type VersionInfo struct {
	PluginVersion string `json:"plugin_version"`
	BuildVersion  string `json:"build_version"`
	BuildCommit   string `json:"build_commit"`
	BuildTime     string `json:"build_time"`
	GoVersion     string `json:"go_version"`
	ModuleVersion string `json:"module_version"`
	Source        string `json:"source"`
}

// GetVersionInfo returns comprehensive version information
func GetVersionInfo() *VersionInfo {
	versionInfoOnce.Do(func() {
		versionInfo = &VersionInfo{
			PluginVersion: PluginVersion,
			BuildVersion:  buildVersion,
			BuildCommit:   buildCommit,
			BuildTime:     buildTime,
			Source:        TelemetrySource,
		}

		// Get Go version and module information from runtime
		if info, ok := debug.ReadBuildInfo(); ok {
			versionInfo.GoVersion = info.GoVersion

			// Try to find module version
			for _, dep := range info.Deps {
				if dep.Path == "github.com/firebase/genkit/go/plugins/googlecloud" {
					versionInfo.ModuleVersion = dep.Version
					break
				}
			}
		}

		// Use build version if no module version found
		if versionInfo.ModuleVersion == "" && buildVersion != "" {
			versionInfo.ModuleVersion = buildVersion
		}

		// Fallback to plugin version
		if versionInfo.ModuleVersion == "" {
			versionInfo.ModuleVersion = PluginVersion
		}
	})

	return versionInfo
}

// GetSourceVersion returns the version string used in telemetry dimensions
func GetSourceVersion() string {
	info := GetVersionInfo()
	if info.BuildVersion != "" {
		return info.BuildVersion
	}
	if info.ModuleVersion != "" {
		return info.ModuleVersion
	}
	return info.PluginVersion
}

// GetUserAgent returns a user agent string for HTTP requests
func GetUserAgent() string {
	info := GetVersionInfo()
	version := GetSourceVersion()
	return fmt.Sprintf("%s/%s (%s)", PluginName, version, info.GoVersion)
}

// IsDevBuild returns true if this appears to be a development build
func IsDevBuild() bool {
	return buildVersion == "" && buildCommit == ""
}

// GetTelemetryDimensions returns standard dimensions for telemetry
func GetTelemetryDimensions() map[string]interface{} {
	return map[string]interface{}{
		"source":        TelemetrySource,
		"sourceVersion": GetSourceVersion(),
	}
}

// Metric name constants to ensure consistency
const (
	// Generate metrics namespace
	MetricNamespaceAI = "ai"

	// Feature metrics namespace
	MetricNamespaceFeature = "feature"

	// Engagement metrics namespace
	MetricNamespaceEngagement = "engagement"
)

// Standard metric names
const (
	// Generate metrics
	MetricGenerateRequests         = "generate/requests"
	MetricGenerateLatency          = "generate/latency"
	MetricGenerateInputTokens      = "generate/input/tokens"
	MetricGenerateInputCharacters  = "generate/input/characters"
	MetricGenerateInputImages      = "generate/input/images"
	MetricGenerateOutputTokens     = "generate/output/tokens"
	MetricGenerateOutputCharacters = "generate/output/characters"
	MetricGenerateOutputImages     = "generate/output/images"

	// Feature metrics
	MetricFeatureRequests = "requests"
	MetricFeatureLatency  = "latency"

	// Path metrics (under feature namespace)
	MetricPathRequests = "path/requests"
	MetricPathLatency  = "path/latency"

	// Engagement metrics
	MetricEngagementFeedback   = "feedback"
	MetricEngagementAcceptance = "acceptance"
)

// Standard log message prefixes
const (
	LogPrefixConfig     = "Config"
	LogPrefixInput      = "Input"
	LogPrefixOutput     = "Output"
	LogPrefixError      = "Error"
	LogPrefixFeedback   = "UserFeedback"
	LogPrefixAcceptance = "UserAcceptance"
)

// Telemetry attribute constants
const (
	AttrGenkitName                    = "genkit:name"
	AttrGenkitPath                    = "genkit:path"
	AttrGenkitType                    = "genkit:type"
	AttrGenkitState                   = "genkit:state"
	AttrGenkitIsRoot                  = "genkit:isRoot"
	AttrGenkitIsFailureSource         = "genkit:isFailureSource"
	AttrGenkitInput                   = "genkit:input"
	AttrGenkitOutput                  = "genkit:output"
	AttrGenkitSessionID               = "genkit:sessionId"
	AttrGenkitThreadName              = "genkit:threadName"
	AttrGenkitMetadataSubtype         = "genkit:metadata:subtype"
	AttrGenkitMetadataFlowName        = "genkit:metadata:flow:name"
	AttrGenkitMetadataFeedbackValue   = "genkit:metadata:feedbackValue"
	AttrGenkitMetadataTextFeedback    = "genkit:metadata:textFeedback"
	AttrGenkitMetadataAcceptanceValue = "genkit:metadata:acceptanceValue"
)

// Error constants
const (
	ErrUnknown          = "<unknown>"
	ErrMissingProjectID = "ProjectID is required"
)

// Performance constants
const (
	DefaultBufferSize     = 1000
	DefaultMetricInterval = 60    // seconds
	DefaultTimeoutMillis  = 60000 // 60 seconds
	MaxAttributeLength    = 1024
	MaxLogContentLength   = 128000 // 128,000 characters
	MaxPathLength         = 4096   // 4,096 characters for paths
)

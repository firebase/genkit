/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Telemetry module for Genkit Java SDK.
 * 
 * <p>
 * This package provides observability utilities for tracking:
 * <ul>
 * <li>Model generation metrics (token counts, latency, etc.)</li>
 * <li>Tool execution metrics</li>
 * <li>Feature/flow-level metrics</li>
 * <li>Action-level metrics</li>
 * </ul>
 * 
 * <p>
 * The telemetry classes integrate with OpenTelemetry for metrics export,
 * allowing Genkit applications to be monitored using standard observability
 * tools like Google Cloud Operations, Prometheus, etc.
 * 
 * <p>
 * Key classes:
 * <ul>
 * <li>{@link com.google.genkit.ai.telemetry.GenerateTelemetry} - Tracks model
 * generation metrics</li>
 * <li>{@link com.google.genkit.ai.telemetry.ToolTelemetry} - Tracks tool
 * execution metrics</li>
 * <li>{@link com.google.genkit.ai.telemetry.FeatureTelemetry} - Tracks
 * feature/flow metrics</li>
 * <li>{@link com.google.genkit.ai.telemetry.ActionTelemetry} - Tracks general
 * action metrics</li>
 * <li>{@link com.google.genkit.ai.telemetry.ModelTelemetryHelper} - Helper for
 * recording model telemetry</li>
 * </ul>
 * 
 * @see <a href="https://opentelemetry.io/">OpenTelemetry</a>
 */
package com.google.genkit.ai.telemetry;

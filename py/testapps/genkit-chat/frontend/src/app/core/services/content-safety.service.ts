/**
 * Copyright 2026 Google LLC
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

import { Injectable, signal } from '@angular/core';

/**
 * Content Safety Service using TensorFlow.js Toxicity model.
 *
 * Detects harmful content client-side before sending to the server.
 * This provides a first line of defense against toxic content.
 */
@Injectable({
  providedIn: 'root',
})
export class ContentSafetyService {
  private toxicityModel: unknown = null;
  private isModelLoading = false;

  // Configurable threshold (0-1, lower = more strict)
  private readonly toxicityThreshold = 0.85;

  /** Whether content safety checks are enabled */
  enabled = signal(true);

  /** Whether the model is ready for use */
  modelReady = signal(false);

  /** Loading status */
  loading = signal(false);

  /**
   * Lazily load the toxicity model.
   * Called on first use to avoid blocking initial page load.
   */
  async loadModel(): Promise<void> {
    if (this.toxicityModel || this.isModelLoading) return;

    this.isModelLoading = true;
    this.loading.set(true);

    try {
      // Dynamic import to reduce initial bundle size
      const toxicity = await import('@tensorflow-models/toxicity');

      // Load with configured threshold
      // Labels: identity_attack, insult, obscene, severe_toxicity,
      //         sexual_explicit, threat, toxicity
      this.toxicityModel = await toxicity.load(this.toxicityThreshold, []);

      this.modelReady.set(true);
    } catch (_error) {
      // Disable safety checks if model fails to load
      this.enabled.set(false);
    } finally {
      this.isModelLoading = false;
      this.loading.set(false);
    }
  }

  /**
   * Check if content is safe to send.
   * Returns true if content is safe, false if harmful content detected.
   */
  async checkContent(text: string): Promise<ContentCheckResult> {
    if (!this.enabled() || !text.trim()) {
      return { safe: true, labels: [] };
    }

    // Load model if not ready
    if (!this.modelReady()) {
      await this.loadModel();
    }

    if (!this.toxicityModel) {
      // Model not available, allow content
      return { safe: true, labels: [] };
    }

    try {
      const model = this.toxicityModel as {
        classify: (text: string[]) => Promise<ToxicityPrediction[]>;
      };
      const predictions = await model.classify([text]);

      const flaggedLabels: string[] = [];

      for (const prediction of predictions) {
        // Check if any result has high probability of being toxic
        const results = prediction.results[0];
        if (results.match === true) {
          flaggedLabels.push(this.formatLabel(prediction.label));
        }
      }

      if (flaggedLabels.length > 0) {
        return {
          safe: false,
          labels: flaggedLabels,
          message: `Content may contain: ${flaggedLabels.join(', ')}`,
        };
      }

      return { safe: true, labels: [] };
    } catch (_error) {
      // On error, allow content to proceed
      return { safe: true, labels: [] };
    }
  }

  /**
   * Toggle content safety on/off.
   */
  toggle(): void {
    this.enabled.update((v) => !v);

    // Load model when enabling if not already loaded
    if (this.enabled() && !this.modelReady()) {
      this.loadModel();
    }
  }

  /**
   * Format label for display.
   */
  private formatLabel(label: string): string {
    return label.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

/**
 * Result of content safety check.
 */
export interface ContentCheckResult {
  safe: boolean;
  labels: string[];
  message?: string;
}

/**
 * TensorFlow toxicity prediction structure.
 */
interface ToxicityPrediction {
  label: string;
  results: Array<{
    probabilities: Float32Array;
    match: boolean | null;
  }>;
}

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

/**
 * Pure utility functions for markdown processing.
 * These functions have no Angular dependencies and are easily testable.
 */

/**
 * Greek letter and math symbol substitutions.
 */
export const MATH_SUBSTITUTIONS: Record<string, string> = {
  '\\alpha': 'α',
  '\\beta': 'β',
  '\\gamma': 'γ',
  '\\delta': 'δ',
  '\\epsilon': 'ε',
  '\\pi': 'π',
  '\\sigma': 'σ',
  '\\omega': 'ω',
  '\\theta': 'θ',
  '\\lambda': 'λ',
  '\\mu': 'μ',
  '\\phi': 'φ',
  '\\infty': '∞',
  '\\sum': '∑',
  '\\int': '∫',
  '\\partial': '∂',
  '\\pm': '±',
  '\\times': '×',
  '\\div': '÷',
  '\\cdot': '·',
  '\\leq': '≤',
  '\\geq': '≥',
  '\\neq': '≠',
  '\\approx': '≈',
  '\\rightarrow': '→',
  '\\leftarrow': '←',
  '\\Rightarrow': '⇒',
  '\\in': '∈',
  '\\subset': '⊂',
  '\\cup': '∪',
  '\\cap': '∩',
  '\\forall': '∀',
  '\\exists': '∃',
  '\\nabla': '∇',
  '\\sqrt': '√',
};

/**
 * Process math symbols synchronously with basic substitutions.
 */
export function processMathSync(content: string): string {
  let result = content;
  for (const [key, value] of Object.entries(MATH_SUBSTITUTIONS)) {
    result = result.split(key).join(value);
  }
  return result;
}

/**
 * Escape HTML characters for safe display.
 */
export function escapeHtml(content: string): string {
  return content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * Add target="_blank" to links for external navigation.
 */
export function addExternalLinkAttributes(html: string): string {
  return html.replace(/<a\s+href=/g, '<a target="_blank" rel="noopener noreferrer" href=');
}

/**
 * Wrap escaped content in a pre element.
 */
export function wrapInPre(content: string): string {
  return `<pre>${escapeHtml(content)}</pre>`;
}

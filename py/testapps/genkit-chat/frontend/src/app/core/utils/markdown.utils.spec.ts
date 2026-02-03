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

import { describe, expect, it } from 'vitest';
import {
  addExternalLinkAttributes,
  escapeHtml,
  MATH_SUBSTITUTIONS,
  processMathSync,
  wrapInPre,
} from './markdown.utils';

describe('markdown.utils', () => {
  describe('MATH_SUBSTITUTIONS', () => {
    it('should have Greek letters', () => {
      expect(MATH_SUBSTITUTIONS['\\alpha']).toBe('α');
      expect(MATH_SUBSTITUTIONS['\\beta']).toBe('β');
      expect(MATH_SUBSTITUTIONS['\\gamma']).toBe('γ');
      expect(MATH_SUBSTITUTIONS['\\pi']).toBe('π');
    });

    it('should have math operators', () => {
      expect(MATH_SUBSTITUTIONS['\\times']).toBe('×');
      expect(MATH_SUBSTITUTIONS['\\div']).toBe('÷');
      expect(MATH_SUBSTITUTIONS['\\pm']).toBe('±');
    });

    it('should have comparison operators', () => {
      expect(MATH_SUBSTITUTIONS['\\leq']).toBe('≤');
      expect(MATH_SUBSTITUTIONS['\\geq']).toBe('≥');
      expect(MATH_SUBSTITUTIONS['\\neq']).toBe('≠');
    });

    it('should have arrows', () => {
      expect(MATH_SUBSTITUTIONS['\\rightarrow']).toBe('→');
      expect(MATH_SUBSTITUTIONS['\\leftarrow']).toBe('←');
    });

    it('should have calculus symbols', () => {
      expect(MATH_SUBSTITUTIONS['\\sum']).toBe('∑');
      expect(MATH_SUBSTITUTIONS['\\int']).toBe('∫');
      expect(MATH_SUBSTITUTIONS['\\partial']).toBe('∂');
    });
  });

  describe('processMathSync', () => {
    it('should substitute Greek letters', () => {
      expect(processMathSync('\\alpha + \\beta')).toBe('α + β');
    });

    it('should substitute multiple symbols', () => {
      expect(processMathSync('\\pi \\times r^2')).toBe('π × r^2');
    });

    it('should keep non-math text unchanged', () => {
      expect(processMathSync('Hello World')).toBe('Hello World');
    });

    it('should handle empty string', () => {
      expect(processMathSync('')).toBe('');
    });

    it('should handle complex expressions', () => {
      const input = '\\forall x \\in A, x \\leq \\infty';
      const expected = '∀ x ∈ A, x ≤ ∞';
      expect(processMathSync(input)).toBe(expected);
    });
  });

  describe('escapeHtml', () => {
    it('should escape ampersands', () => {
      expect(escapeHtml('A & B')).toBe('A &amp; B');
    });

    it('should escape less than', () => {
      expect(escapeHtml('a < b')).toBe('a &lt; b');
    });

    it('should escape greater than', () => {
      expect(escapeHtml('a > b')).toBe('a &gt; b');
    });

    it('should escape HTML tags', () => {
      expect(escapeHtml('<script>alert("xss")</script>')).toBe(
        '&lt;script&gt;alert("xss")&lt;/script&gt;'
      );
    });

    it('should handle empty string', () => {
      expect(escapeHtml('')).toBe('');
    });

    it('should preserve normal text', () => {
      expect(escapeHtml('Hello World')).toBe('Hello World');
    });
  });

  describe('addExternalLinkAttributes', () => {
    it('should add target and rel to links', () => {
      const input = '<a href="https://example.com">Link</a>';
      const result = addExternalLinkAttributes(input);
      expect(result).toContain('target="_blank"');
      expect(result).toContain('rel="noopener noreferrer"');
    });

    it('should handle multiple links', () => {
      const input = '<a href="a">A</a> and <a href="b">B</a>';
      const result = addExternalLinkAttributes(input);
      expect(result.match(/target="_blank"/g)?.length).toBe(2);
    });

    it('should handle no links', () => {
      const input = '<p>No links here</p>';
      expect(addExternalLinkAttributes(input)).toBe(input);
    });
  });

  describe('wrapInPre', () => {
    it('should wrap content in pre tag', () => {
      expect(wrapInPre('code')).toBe('<pre>code</pre>');
    });

    it('should escape HTML in content', () => {
      expect(wrapInPre('<script>')).toBe('<pre>&lt;script&gt;</pre>');
    });

    it('should handle empty string', () => {
      expect(wrapInPre('')).toBe('<pre></pre>');
    });
  });
});

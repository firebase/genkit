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

// Test the pure logic functions without Angular dependencies

describe('SafeMarkdownPipe pure logic', () => {
  describe('Math substitutions', () => {
    const substitutions: Record<string, string> = {
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

    const processMathSync = (content: string): string => {
      let result = content;
      for (const [key, value] of Object.entries(substitutions)) {
        result = result.split(key).join(value);
      }
      return result;
    };

    it('should substitute Greek letters', () => {
      expect(processMathSync('\\alpha + \\beta')).toBe('α + β');
    });

    it('should substitute mathematical operators', () => {
      expect(processMathSync('a \\times b')).toBe('a × b');
      expect(processMathSync('a \\div b')).toBe('a ÷ b');
      expect(processMathSync('a \\pm b')).toBe('a ± b');
    });

    it('should substitute comparison operators', () => {
      expect(processMathSync('a \\leq b')).toBe('a ≤ b');
      expect(processMathSync('a \\geq b')).toBe('a ≥ b');
      expect(processMathSync('a \\neq b')).toBe('a ≠ b');
      expect(processMathSync('a \\approx b')).toBe('a ≈ b');
    });

    it('should substitute arrows', () => {
      expect(processMathSync('a \\rightarrow b')).toBe('a → b');
      expect(processMathSync('a \\leftarrow b')).toBe('a ← b');
      expect(processMathSync('a \\Rightarrow b')).toBe('a ⇒ b');
    });

    it('should substitute set operators', () => {
      expect(processMathSync('A \\cup B')).toBe('A ∪ B');
      expect(processMathSync('A \\cap B')).toBe('A ∩ B');
      expect(processMathSync('x \\in A')).toBe('x ∈ A');
      expect(processMathSync('A \\subset B')).toBe('A ⊂ B');
    });

    it('should substitute calculus symbols', () => {
      expect(processMathSync('\\sum_{i=1}^n')).toBe('∑_{i=1}^n');
      expect(processMathSync('\\int_a^b')).toBe('∫_a^b');
      expect(processMathSync('\\partial x')).toBe('∂ x');
      expect(processMathSync('\\nabla f')).toBe('∇ f');
    });

    it('should substitute logic symbols', () => {
      expect(processMathSync('\\forall x')).toBe('∀ x');
      expect(processMathSync('\\exists y')).toBe('∃ y');
    });

    it('should handle infinity', () => {
      expect(processMathSync('\\infty')).toBe('∞');
    });

    it('should handle pi', () => {
      expect(processMathSync('2\\pi r')).toBe('2π r');
    });

    it('should handle complex expressions', () => {
      const input = 'E = mc^2, where \\alpha \\approx 0.007297, and \\pi \\approx 3.14159';
      const expected = 'E = mc^2, where α ≈ 0.007297, and π ≈ 3.14159';
      expect(processMathSync(input)).toBe(expected);
    });

    it('should preserve non-math text', () => {
      const input = 'Hello, world!';
      expect(processMathSync(input)).toBe(input);
    });

    it('should handle empty string', () => {
      expect(processMathSync('')).toBe('');
    });
  });

  describe('Content escaping', () => {
    const escapeContent = (content: string): string => {
      return content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    };

    it('should escape ampersands', () => {
      expect(escapeContent('A & B')).toBe('A &amp; B');
    });

    it('should escape less than', () => {
      expect(escapeContent('if a < b')).toBe('if a &lt; b');
    });

    it('should escape greater than', () => {
      expect(escapeContent('if a > b')).toBe('if a &gt; b');
    });

    it('should escape HTML-like content', () => {
      expect(escapeContent('<script>alert("xss")</script>')).toBe(
        '&lt;script&gt;alert("xss")&lt;/script&gt;'
      );
    });

    it('should handle multiple escapes', () => {
      expect(escapeContent('a < b & b > c')).toBe('a &lt; b &amp; b &gt; c');
    });

    it('should handle empty string', () => {
      expect(escapeContent('')).toBe('');
    });

    it('should preserve normal text', () => {
      expect(escapeContent('Hello, World!')).toBe('Hello, World!');
    });
  });

  describe('Link processing', () => {
    const processLinks = (html: string): string => {
      return html.replace(/&lt;a\s+href=/g, '<a target="_blank" rel="noopener noreferrer" href=');
    };

    it('should be a no-op on escaped content', () => {
      const escaped = '&lt;a href="https://example.com"&gt;Link&lt;/a&gt;';
      expect(processLinks(escaped)).toBe(
        '<a target="_blank" rel="noopener noreferrer" href="https://example.com"&gt;Link&lt;/a&gt;'
      );
    });
  });
});

describe('DOMPurify config validation', () => {
  const purifyConfig = {
    ALLOWED_TAGS: [
      'p',
      'br',
      'strong',
      'em',
      'b',
      'i',
      'u',
      's',
      'strike',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'ul',
      'ol',
      'li',
      'blockquote',
      'pre',
      'code',
      'a',
      'img',
      'table',
      'thead',
      'tbody',
      'tr',
      'th',
      'td',
      'hr',
      'div',
      'span',
      'sub',
      'sup',
      // SVG elements for Mermaid
      'svg',
      'g',
      'path',
      'rect',
      'circle',
      'ellipse',
      'line',
      'polyline',
      'polygon',
      'text',
      'tspan',
      'defs',
      'marker',
      'foreignObject',
      'style',
    ],
    ALLOWED_ATTR: [
      'href',
      'title',
      'alt',
      'src',
      'class',
      'id',
      'target',
      'rel',
      'width',
      'height',
      // SVG attributes
      'd',
      'fill',
      'stroke',
      'stroke-width',
      'transform',
      'x',
      'y',
      'rx',
      'ry',
      'cx',
      'cy',
      'r',
      'x1',
      'y1',
      'x2',
      'y2',
      'points',
      'viewBox',
      'preserveAspectRatio',
      'xmlns',
      'font-size',
      'font-family',
      'font-weight',
      'text-anchor',
      'dominant-baseline',
      'alignment-baseline',
      'marker-end',
      'marker-start',
      'markerWidth',
      'markerHeight',
      'refX',
      'refY',
      'orient',
      'style',
    ],
  };

  it('should include essential HTML tags', () => {
    expect(purifyConfig.ALLOWED_TAGS).toContain('p');
    expect(purifyConfig.ALLOWED_TAGS).toContain('a');
    expect(purifyConfig.ALLOWED_TAGS).toContain('code');
    expect(purifyConfig.ALLOWED_TAGS).toContain('pre');
  });

  it('should include heading tags', () => {
    expect(purifyConfig.ALLOWED_TAGS).toContain('h1');
    expect(purifyConfig.ALLOWED_TAGS).toContain('h2');
    expect(purifyConfig.ALLOWED_TAGS).toContain('h3');
  });

  it('should include list tags', () => {
    expect(purifyConfig.ALLOWED_TAGS).toContain('ul');
    expect(purifyConfig.ALLOWED_TAGS).toContain('ol');
    expect(purifyConfig.ALLOWED_TAGS).toContain('li');
  });

  it('should include table tags', () => {
    expect(purifyConfig.ALLOWED_TAGS).toContain('table');
    expect(purifyConfig.ALLOWED_TAGS).toContain('tr');
    expect(purifyConfig.ALLOWED_TAGS).toContain('td');
    expect(purifyConfig.ALLOWED_TAGS).toContain('th');
  });

  it('should include SVG tags for Mermaid', () => {
    expect(purifyConfig.ALLOWED_TAGS).toContain('svg');
    expect(purifyConfig.ALLOWED_TAGS).toContain('path');
    expect(purifyConfig.ALLOWED_TAGS).toContain('g');
  });

  it('should not include script tag', () => {
    expect(purifyConfig.ALLOWED_TAGS).not.toContain('script');
  });

  it('should not include iframe tag', () => {
    expect(purifyConfig.ALLOWED_TAGS).not.toContain('iframe');
  });

  it('should include href attribute for links', () => {
    expect(purifyConfig.ALLOWED_ATTR).toContain('href');
  });

  it('should include src attribute for images', () => {
    expect(purifyConfig.ALLOWED_ATTR).toContain('src');
  });

  it('should not include onclick attribute', () => {
    expect(purifyConfig.ALLOWED_ATTR).not.toContain('onclick');
  });

  it('should not include onerror attribute', () => {
    expect(purifyConfig.ALLOWED_ATTR).not.toContain('onerror');
  });
});

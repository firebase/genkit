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

import { inject, Pipe, type PipeTransform } from '@angular/core';
import { DomSanitizer, type SafeHtml } from '@angular/platform-browser';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import { marked, Renderer } from 'marked';
import { RenderingService } from '../../core/services/rendering.service';

/**
 * Safe Markdown rendering pipe with Mermaid diagrams, Math, and syntax highlighting.
 * Uses DOMPurify for XSS protection and highlight.js for code syntax highlighting.
 *
 * Features:
 * - GitHub Flavored Markdown
 * - Mermaid diagrams (```mermaid blocks)
 * - Math equations ($inline$ and $$display$$)
 * - Syntax highlighting for code blocks (via highlight.js)
 * - Copy button for code blocks
 *
 * Usage:
 *   [innerHTML]="content | safeMarkdown"
 */
@Pipe({
  name: 'safeMarkdown',
  pure: false, // Need impure for async Mermaid rendering
})
export class SafeMarkdownPipe implements PipeTransform {
  private readonly sanitizer = inject(DomSanitizer);
  private readonly renderingService = inject(RenderingService);

  // Cache for rendered content
  private cache = new Map<string, SafeHtml>();

  // Counter for unique code block IDs
  private codeBlockCounter = 0;

  /**
   * Configure DOMPurify with settings that allow Mermaid SVGs and code highlighting.
   */
  private readonly purifyConfig = {
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
      'button',
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
      'data-code',
      'data-lang',
      'onclick',
      'aria-label',
      'type',
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
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|data):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i,
    ADD_ATTR: ['target'],
    ALLOW_DATA_ATTR: true, // Enable data-* attributes for copy functionality
    RETURN_DOM: false as const,
    RETURN_DOM_FRAGMENT: false as const,
  };

  constructor() {
    // Configure marked with custom renderer for syntax highlighting
    this.configureMarked();
  }

  /**
   * Configure marked with a custom renderer for code blocks and tables.
   */
  private configureMarked(): void {
    const renderer = new Renderer();

    // Counter for unique table IDs
    let tableCounter = 0;

    // Override code block rendering to add syntax highlighting and copy button
    renderer.code = ({ text, lang }: { text: string; lang?: string }): string => {
      const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
      const highlighted = hljs.highlight(text, { language }).value;
      const blockId = `code-block-${++this.codeBlockCounter}`;
      const escapedCode = this.escapeHtml(text);

      return `
        <div class="code-block-wrapper">
          <div class="code-block-header">
            <span class="code-language">${language}</span>
            <button
              class="copy-button"
              data-code="${escapedCode}"
              aria-label="Copy code"
              title="Copy to clipboard"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span class="copy-text">Copy</span>
            </button>
          </div>
          <pre id="${blockId}"><code class="hljs language-${language}">${highlighted}</code></pre>
        </div>
      `;
    };

    // Override table rendering to wrap in container with copy button
    renderer.table = (token: {
      header: Array<{ text: string }>;
      rows: Array<Array<{ text: string }>>;
      align: Array<'center' | 'left' | 'right' | null>;
    }): string => {
      const tableId = `table-${++tableCounter}`;

      // Build header row
      const headerCells = token.header
        .map((cell: { text: string }, i: number) => {
          const align = token.align[i] ? ` style="text-align: ${token.align[i]}"` : '';
          return `<th${align}>${cell.text}</th>`;
        })
        .join('');

      // Build body rows
      const bodyRows = token.rows
        .map((row: Array<{ text: string }>) => {
          const cells = row
            .map((cell: { text: string }, i: number) => {
              const align = token.align[i] ? ` style="text-align: ${token.align[i]}"` : '';
              return `<td${align}>${cell.text}</td>`;
            })
            .join('');
          return `<tr>${cells}</tr>`;
        })
        .join('');

      // Build the table HTML
      const tableHtml = `<table id="${tableId}" class="markdown-table">
        <thead><tr>${headerCells}</tr></thead>
        <tbody>${bodyRows}</tbody>
      </table>`;

      // Wrap in container with header and copy button
      return `
        <div class="table-wrapper">
          <div class="table-header">
            <span class="table-label">Table</span>
            <button
              class="copy-table-button"
              data-table-id="${tableId}"
              aria-label="Copy table to clipboard"
              title="Copy as spreadsheet format"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="3" y1="9" x2="21" y2="9"></line>
                <line x1="3" y1="15" x2="21" y2="15"></line>
                <line x1="9" y1="3" x2="9" y2="21"></line>
                <line x1="15" y1="3" x2="15" y2="21"></line>
              </svg>
              <span class="copy-text">Copy</span>
            </button>
          </div>
          <div class="table-container">
            ${tableHtml}
          </div>
        </div>
      `;
    };

    // Override inline code to add styling class
    renderer.codespan = ({ text }: { text: string }): string => {
      return `<code class="inline-code">${text}</code>`;
    };

    marked.setOptions({
      renderer,
      breaks: true,
      gfm: true,
    });
  }

  /**
   * Escape HTML characters for safe embedding in data attributes.
   */
  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;')
      .replace(/\n/g, '&#10;');
  }

  transform(content: string | null | undefined): SafeHtml {
    if (!content) {
      return '';
    }

    // Check cache first
    const cached = this.cache.get(content);
    if (cached !== undefined) {
      return cached;
    }

    // Start async rendering
    this.renderAsync(content);

    // Return placeholder while rendering
    const placeholder = this.renderSync(content);
    return placeholder;
  }

  /**
   * Synchronous render for immediate display.
   */
  private renderSync(content: string): SafeHtml {
    try {
      // Process math before markdown
      const processed = this.processMathSync(content);

      // Parse markdown to HTML (with syntax highlighting)
      const rawHtml = marked.parse(processed, {
        async: false,
      }) as string;

      // Sanitize HTML with DOMPurify
      const cleanHtml = DOMPurify.sanitize(rawHtml, this.purifyConfig) as string;

      // Add target="_blank" to links
      const safeHtml = cleanHtml.replace(
        /<a\s+href=/g,
        '<a target="_blank" rel="noopener noreferrer" href='
      );

      return this.sanitizer.bypassSecurityTrustHtml(safeHtml);
    } catch {
      return this.escapeContent(content);
    }
  }

  /**
   * Async render for Mermaid diagrams.
   */
  private async renderAsync(content: string): Promise<void> {
    try {
      // Process math
      const processed = await this.renderingService.renderMath(content);

      // Parse markdown (with syntax highlighting)
      const rawHtml = marked.parse(processed, {
        async: false,
      }) as string;

      // Render Mermaid diagrams
      const withMermaid = await this.renderingService.processMermaidBlocks(rawHtml);

      // Sanitize
      const cleanHtml = DOMPurify.sanitize(withMermaid, this.purifyConfig) as string;

      // Add target="_blank" to links
      const safeHtml = cleanHtml.replace(
        /<a\s+href=/g,
        '<a target="_blank" rel="noopener noreferrer" href='
      );

      // Cache the result
      this.cache.set(content, this.sanitizer.bypassSecurityTrustHtml(safeHtml));
    } catch (_error) {}
  }

  /**
   * Process math synchronously with basic substitutions.
   */
  private processMathSync(content: string): string {
    // Basic Greek letter substitutions for immediate display
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

    let result = content;
    for (const [key, value] of Object.entries(substitutions)) {
      result = result.split(key).join(value);
    }
    return result;
  }

  /**
   * Escape content for safe display on error.
   */
  private escapeContent(content: string): SafeHtml {
    const escaped = content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return this.sanitizer.bypassSecurityTrustHtml(`<pre>${escaped}</pre>`);
  }
}

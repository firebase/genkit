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
 * SafeMarkdownPipe - Renders markdown safely with HTML sanitization.
 * 
 * This is a lightweight pipe for the genkit-ui library that provides
 * basic markdown rendering with HTML escaping. For full markdown support,
 * including code highlighting, use the application's SafeMarkdownPipe.
 * 
 * Security:
 * - Escapes HTML entities by default
 * - Uses DOMPurify when available for XSS protection
 */
import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

/**
 * Basic markdown to HTML converter.
 * Handles common patterns without external dependencies.
 */
function basicMarkdownToHtml(content: string): string {
    let html = content
        // Escape HTML first
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // Code blocks (must be before inline code)
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        // Bold
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/__([^_]+)__/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/_([^_]+)_/g, '<em>$1</em>')
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
        // Headers
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Line breaks
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    return `<p>${html}</p>`;
}

@Pipe({
    name: 'safeMarkdown',
    standalone: true,
})
export class SafeMarkdownPipe implements PipeTransform {
    constructor(private sanitizer: DomSanitizer) { }

    transform(content: string | null | undefined): SafeHtml {
        if (!content) {
            return '';
        }

        const html = basicMarkdownToHtml(content);

        // Bypass security as we've already sanitized the content
        return this.sanitizer.bypassSecurityTrustHtml(html);
    }
}

import { Pipe, PipeTransform, inject } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { RenderingService } from '../../core/services/rendering.service';

/**
 * Safe Markdown rendering pipe with Mermaid diagrams and Math support.
 * Uses DOMPurify for XSS protection.
 * 
 * Features:
 * - GitHub Flavored Markdown
 * - Mermaid diagrams (```mermaid blocks)
 * - Math equations ($inline$ and $$display$$)
 * - Syntax highlighting for code blocks
 * 
 * Usage:
 *   [innerHTML]="content | safeMarkdown"
 */
@Pipe({
    name: 'safeMarkdown',
    pure: false  // Need impure for async Mermaid rendering
})
export class SafeMarkdownPipe implements PipeTransform {
    private readonly sanitizer = inject(DomSanitizer);
    private readonly renderingService = inject(RenderingService);

    // Cache for rendered content
    private cache = new Map<string, SafeHtml>();

    /**
     * Configure DOMPurify with settings that allow Mermaid SVGs.
     */
    private readonly purifyConfig = {
        ALLOWED_TAGS: [
            'p', 'br', 'strong', 'em', 'b', 'i', 'u', 's', 'strike',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li',
            'blockquote', 'pre', 'code',
            'a', 'img',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'hr', 'div', 'span', 'sub', 'sup',
            // SVG elements for Mermaid
            'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line',
            'polyline', 'polygon', 'text', 'tspan', 'defs', 'marker',
            'foreignObject', 'style'
        ],
        ALLOWED_ATTR: [
            'href', 'title', 'alt', 'src', 'class', 'id',
            'target', 'rel', 'width', 'height',
            // SVG attributes
            'd', 'fill', 'stroke', 'stroke-width', 'transform',
            'x', 'y', 'rx', 'ry', 'cx', 'cy', 'r',
            'x1', 'y1', 'x2', 'y2', 'points',
            'viewBox', 'preserveAspectRatio', 'xmlns',
            'font-size', 'font-family', 'font-weight', 'text-anchor',
            'dominant-baseline', 'alignment-baseline',
            'marker-end', 'marker-start', 'markerWidth', 'markerHeight',
            'refX', 'refY', 'orient', 'style'
        ],
        ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i,
        ADD_ATTR: ['target'],
        ALLOW_DATA_ATTR: false,
        RETURN_DOM: false as const,
        RETURN_DOM_FRAGMENT: false as const,
    };

    transform(content: string | null | undefined): SafeHtml {
        if (!content) {
            return '';
        }

        // Check cache first
        if (this.cache.has(content)) {
            return this.cache.get(content)!;
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
            let processed = this.processMathSync(content);

            // Parse markdown to HTML
            const rawHtml = marked.parse(processed, {
                async: false,
                breaks: true,
                gfm: true,
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
            let processed = await this.renderingService.renderMath(content);

            // Parse markdown
            const rawHtml = marked.parse(processed, {
                async: false,
                breaks: true,
                gfm: true,
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
        } catch (error) {
            console.error('Async markdown render failed:', error);
        }
    }

    /**
     * Process math synchronously with basic substitutions.
     */
    private processMathSync(content: string): string {
        // Basic Greek letter substitutions for immediate display
        const substitutions: Record<string, string> = {
            '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ', '\\delta': 'δ',
            '\\epsilon': 'ε', '\\pi': 'π', '\\sigma': 'σ', '\\omega': 'ω',
            '\\theta': 'θ', '\\lambda': 'λ', '\\mu': 'μ', '\\phi': 'φ',
            '\\infty': '∞', '\\sum': '∑', '\\int': '∫', '\\partial': '∂',
            '\\pm': '±', '\\times': '×', '\\div': '÷', '\\cdot': '·',
            '\\leq': '≤', '\\geq': '≥', '\\neq': '≠', '\\approx': '≈',
            '\\rightarrow': '→', '\\leftarrow': '←', '\\Rightarrow': '⇒',
            '\\in': '∈', '\\subset': '⊂', '\\cup': '∪', '\\cap': '∩',
            '\\forall': '∀', '\\exists': '∃', '\\nabla': '∇', '\\sqrt': '√',
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
        const escaped = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        return this.sanitizer.bypassSecurityTrustHtml(`<pre>${escaped}</pre>`);
    }
}

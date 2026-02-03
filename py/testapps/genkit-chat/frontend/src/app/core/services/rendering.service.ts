import { Injectable, signal } from '@angular/core';

/**
 * Service for rendering Mermaid diagrams and MathJax equations.
 * Uses lazy loading to avoid blocking initial page load.
 */
@Injectable({
    providedIn: 'root'
})
export class RenderingService {
    private mermaidModule: typeof import('mermaid') | null = null;
    private mermaidInitialized = false;

    /** Whether Mermaid is ready */
    mermaidReady = signal(false);

    /** Whether MathJax is ready */
    mathjaxReady = signal(false);

    /** Counter for unique diagram IDs */
    private diagramCounter = 0;

    /**
     * Initialize Mermaid for diagram rendering.
     */
    async initMermaid(): Promise<void> {
        if (this.mermaidInitialized) return;

        try {
            this.mermaidModule = await import('mermaid');
            this.mermaidModule.default.initialize({
                startOnLoad: false,
                theme: 'neutral',
                securityLevel: 'strict',
                fontFamily: 'Inter, sans-serif',
                flowchart: {
                    curve: 'basis',
                    padding: 20
                },
                sequence: {
                    diagramMarginX: 50,
                    diagramMarginY: 10
                }
            });
            this.mermaidInitialized = true;
            this.mermaidReady.set(true);
            console.log('Mermaid initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Mermaid:', error);
        }
    }

    /**
     * Render a Mermaid diagram from definition.
     * Returns SVG string or error message.
     */
    async renderMermaid(definition: string): Promise<string> {
        if (!this.mermaidInitialized) {
            await this.initMermaid();
        }

        if (!this.mermaidModule) {
            return `<div class="mermaid-error">Mermaid not available</div>`;
        }

        try {
            const id = `mermaid-${++this.diagramCounter}`;
            const { svg } = await this.mermaidModule.default.render(id, definition);
            return `<div class="mermaid-diagram">${svg}</div>`;
        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : 'Unknown error';
            return `<div class="mermaid-error">Diagram error: ${errorMsg}</div>`;
        }
    }

    /**
     * Render MathJax equations.
     * Supports both inline ($...$) and display ($$...$$) math.
     */
    async renderMath(content: string): Promise<string> {
        // Simple regex-based math rendering
        // For inline: $...$
        // For display: $$...$$

        // Replace display math first (greedy)
        let result = content.replace(/\$\$([^$]+)\$\$/g, (_, math) => {
            return this.renderMathToHtml(math.trim(), true);
        });

        // Replace inline math
        result = result.replace(/\$([^$\n]+)\$/g, (_, math) => {
            return this.renderMathToHtml(math.trim(), false);
        });

        return result;
    }

    /**
     * Convert LaTeX to HTML using basic substitutions.
     * For production, use full MathJax, but this provides basic support.
     */
    private renderMathToHtml(latex: string, display: boolean): string {
        // Basic LaTeX to HTML/Unicode substitutions
        const substitutions: Record<string, string> = {
            '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ', '\\delta': 'δ',
            '\\epsilon': 'ε', '\\zeta': 'ζ', '\\eta': 'η', '\\theta': 'θ',
            '\\iota': 'ι', '\\kappa': 'κ', '\\lambda': 'λ', '\\mu': 'μ',
            '\\nu': 'ν', '\\xi': 'ξ', '\\pi': 'π', '\\rho': 'ρ',
            '\\sigma': 'σ', '\\tau': 'τ', '\\upsilon': 'υ', '\\phi': 'φ',
            '\\chi': 'χ', '\\psi': 'ψ', '\\omega': 'ω',
            '\\Alpha': 'Α', '\\Beta': 'Β', '\\Gamma': 'Γ', '\\Delta': 'Δ',
            '\\Epsilon': 'Ε', '\\Zeta': 'Ζ', '\\Eta': 'Η', '\\Theta': 'Θ',
            '\\Iota': 'Ι', '\\Kappa': 'Κ', '\\Lambda': 'Λ', '\\Mu': 'Μ',
            '\\Nu': 'Ν', '\\Xi': 'Ξ', '\\Pi': 'Π', '\\Rho': 'Ρ',
            '\\Sigma': 'Σ', '\\Tau': 'Τ', '\\Upsilon': 'Υ', '\\Phi': 'Φ',
            '\\Chi': 'Χ', '\\Psi': 'Ψ', '\\Omega': 'Ω',
            '\\infty': '∞', '\\partial': '∂', '\\nabla': '∇',
            '\\sum': '∑', '\\prod': '∏', '\\int': '∫',
            '\\sqrt': '√', '\\pm': '±', '\\mp': '∓',
            '\\times': '×', '\\div': '÷', '\\cdot': '·',
            '\\leq': '≤', '\\geq': '≥', '\\neq': '≠',
            '\\approx': '≈', '\\equiv': '≡', '\\sim': '∼',
            '\\in': '∈', '\\notin': '∉', '\\subset': '⊂',
            '\\supset': '⊃', '\\subseteq': '⊆', '\\supseteq': '⊇',
            '\\cup': '∪', '\\cap': '∩', '\\emptyset': '∅',
            '\\forall': '∀', '\\exists': '∃', '\\neg': '¬',
            '\\wedge': '∧', '\\vee': '∨', '\\Rightarrow': '⇒',
            '\\Leftarrow': '⇐', '\\Leftrightarrow': '⇔',
            '\\rightarrow': '→', '\\leftarrow': '←', '\\leftrightarrow': '↔',
            '\\to': '→',
            '\\langle': '⟨', '\\rangle': '⟩',
            '\\lfloor': '⌊', '\\rfloor': '⌋',
            '\\lceil': '⌈', '\\rceil': '⌉',
        };

        let html = latex;

        // Apply substitutions
        for (const [key, value] of Object.entries(substitutions)) {
            html = html.split(key).join(value);
        }

        // Handle subscripts: x_n or x_{abc}
        html = html.replace(/_\{([^}]+)\}/g, '<sub>$1</sub>');
        html = html.replace(/_([a-zA-Z0-9])/g, '<sub>$1</sub>');

        // Handle superscripts: x^n or x^{abc}
        html = html.replace(/\^\{([^}]+)\}/g, '<sup>$1</sup>');
        html = html.replace(/\^([a-zA-Z0-9])/g, '<sup>$1</sup>');

        // Handle fractions: \frac{a}{b}
        html = html.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g,
            '<span class="math-frac"><span class="math-num">$1</span><span class="math-denom">$2</span></span>');

        // Clean up remaining backslashes and braces
        html = html.replace(/\\[a-zA-Z]+/g, ''); // Remove unknown commands
        html = html.replace(/[{}]/g, ''); // Remove braces

        const className = display ? 'math-display' : 'math-inline';
        return `<span class="${className}">${html}</span>`;
    }

    /**
     * Process content to extract and render Mermaid diagrams.
     * Looks for ```mermaid code blocks.
     */
    async processMermaidBlocks(html: string): Promise<string> {
        // Match mermaid code blocks
        const mermaidRegex = /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/gi;
        const matches = [...html.matchAll(mermaidRegex)];

        if (matches.length === 0) {
            return html;
        }

        let result = html;
        for (const match of matches) {
            const definition = this.decodeHtmlEntities(match[1]);
            const rendered = await this.renderMermaid(definition);
            result = result.replace(match[0], rendered);
        }

        return result;
    }

    /**
     * Decode HTML entities back to characters.
     */
    private decodeHtmlEntities(text: string): string {
        const entities: Record<string, string> = {
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
        };

        let result = text;
        for (const [entity, char] of Object.entries(entities)) {
            result = result.split(entity).join(char);
        }
        return result;
    }
}

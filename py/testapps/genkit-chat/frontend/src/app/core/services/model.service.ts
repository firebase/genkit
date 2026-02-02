import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { catchError, of, tap } from 'rxjs';

/**
 * Model information from the backend.
 */
export interface Model {
    id: string;
    name: string;
    capabilities: string[];
    context_window?: number;
}

/**
 * Provider with available models.
 */
export interface Provider {
    id: string;
    name: string;
    available: boolean;
    models: Model[];
}

/**
 * Service for fetching available models from the backend.
 * Falls back to demo models if backend is unavailable.
 */
@Injectable({
    providedIn: 'root',
})
export class ModelService {
    private http = inject(HttpClient);
    private apiUrl = '/api';

    // All providers with their models
    providers = signal<Provider[]>([]);
    isLoading = signal(false);
    error = signal<string | null>(null);

    // Flattened list of all available models
    allModels = computed(() =>
        this.providers().flatMap(p =>
            p.models.map(m => ({
                ...m,
                provider: p.name,
                providerId: p.id,
            }))
        )
    );

    // Default model (first available or Ollama local)
    defaultModel = computed(() => this.allModels()[0]?.id || 'ollama/llama3.2');

    // Demo models for when backend is unavailable
    private readonly DEMO_PROVIDERS: Provider[] = [
        {
            id: 'google-genai',
            name: 'Google AI',
            available: true,
            models: [
                { id: 'googleai/gemini-3-flash-preview', name: 'Gemini 3 Flash Preview', capabilities: ['text', 'vision', 'streaming'] },
                { id: 'googleai/gemini-3-pro-preview', name: 'Gemini 3 Pro Preview', capabilities: ['text', 'vision', 'streaming'] },
                { id: 'googleai/gemini-2.0-flash', name: 'Gemini 2.0 Flash', capabilities: ['text', 'vision', 'streaming'] },
            ],
        },
        {
            id: 'anthropic',
            name: 'Anthropic',
            available: true,
            models: [
                { id: 'anthropic/claude-sonnet-4-20250514', name: 'Claude Sonnet 4', capabilities: ['text', 'vision', 'streaming'] },
                { id: 'anthropic/claude-3-7-sonnet', name: 'Claude 3.7 Sonnet', capabilities: ['text', 'vision', 'streaming'] },
            ],
        },
        {
            id: 'openai',
            name: 'OpenAI',
            available: true,
            models: [
                { id: 'openai/gpt-4.1', name: 'GPT-4.1', capabilities: ['text', 'vision', 'streaming'] },
                { id: 'openai/gpt-4o', name: 'GPT-4o', capabilities: ['text', 'vision', 'streaming'] },
            ],
        },
    ];

    constructor() {
        // Fetch models on service initialization
        this.fetchModels();
    }

    /**
     * Fetch available models from the backend.
     * Falls back to demo models if backend is unavailable.
     */
    fetchModels(): void {
        this.isLoading.set(true);
        this.error.set(null);

        this.http.get<Provider[]>(`${this.apiUrl}/models`)
            .pipe(
                tap(providers => {
                    this.providers.set(providers);
                    this.isLoading.set(false);
                    console.log('Loaded models from backend:', providers);
                }),
                catchError(err => {
                    console.warn('Backend unavailable, using demo models:', err.message);
                    this.providers.set(this.DEMO_PROVIDERS);
                    this.error.set('Using demo models (backend unavailable)');
                    this.isLoading.set(false);
                    return of(this.DEMO_PROVIDERS);
                }),
            )
            .subscribe();
    }

    /**
     * Get a model by its ID.
     */
    getModel(id: string): Model | undefined {
        return this.allModels().find(m => m.id === id);
    }

    /**
     * Get the provider name for a model ID.
     */
    getProviderName(modelId: string): string {
        const model = this.allModels().find(m => m.id === modelId);
        return (model as any)?.provider || 'Unknown';
    }

    /**
     * Check if a model supports a capability.
     */
    hasCapability(modelId: string, capability: string): boolean {
        const model = this.getModel(modelId);
        return model?.capabilities?.includes(capability) ?? false;
    }
}

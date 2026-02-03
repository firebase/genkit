import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: Date;
    model?: string;
    isError?: boolean;
    errorDetails?: string;
}

export interface ChatRequest {
    message: string;
    model: string;
    history?: { role: string; content: string }[];
}

export interface ChatResponse {
    response: string;
    model: string;
    latency_ms: number;
    isError?: boolean;
    errorDetails?: string;
}

export interface CompareRequest {
    prompt: string;
    models: string[];
}

export interface CompareResponse {
    prompt: string;
    responses: {
        model: string;
        response: string | null;
        latency_ms: number;
        error: string | null;
    }[];
}

@Injectable({
    providedIn: 'root',
})
export class ChatService {
    private http = inject(HttpClient);
    private apiUrl = '/api';

    messages = signal<Message[]>([]);
    isLoading = signal(false);

    sendMessage(message: string, model: string): Observable<ChatResponse> {
        const history = this.messages().map(m => ({
            role: m.role,
            content: m.content,
        }));

        // Add user message to history immediately
        this.messages.update(msgs => [
            ...msgs,
            { role: 'user', content: message, timestamp: new Date() },
        ]);

        this.isLoading.set(true);

        return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, {
            message,
            model,
            history,
        }).pipe(
            catchError(error => {
                console.error('Chat error:', error);
                const errorMessage = error?.error?.detail || error?.error?.message || error?.message || 'Unknown error';
                const errorDetails = JSON.stringify(error, null, 2);
                return of({
                    response: `Error: ${errorMessage}`,
                    model,
                    latency_ms: 0,
                    isError: true,
                    errorDetails
                });
            }),
        );
    }

    addAssistantMessage(response: ChatResponse): void {
        this.messages.update(msgs => [
            ...msgs,
            {
                role: 'assistant',
                content: response.response,
                timestamp: new Date(),
                model: response.model,
                isError: response.isError,
                errorDetails: response.errorDetails,
            },
        ]);
        this.isLoading.set(false);
    }

    // Streaming mode (enabled by default)
    streamingMode = signal(true);

    toggleStreamingMode(): void {
        this.streamingMode.update(v => !v);
    }

    // Send message with streaming (returns EventSource URL)
    sendStreamMessage(message: string, model: string): void {
        const history = this.messages().map(m => ({
            role: m.role,
            content: m.content,
        }));

        // Add user message to history immediately
        this.messages.update(msgs => [
            ...msgs,
            { role: 'user', content: message, timestamp: new Date() },
        ]);

        this.isLoading.set(true);

        // Add placeholder assistant message
        this.messages.update(msgs => [
            ...msgs,
            { role: 'assistant', content: '', timestamp: new Date(), model },
        ]);

        const eventSource = new EventSource(
            `${this.apiUrl}/stream?message=${encodeURIComponent(message)}&model=${encodeURIComponent(model)}&history=${encodeURIComponent(JSON.stringify(history))}`
        );

        eventSource.onmessage = (event) => {
            if (event.data === '[DONE]') {
                eventSource.close();
                this.isLoading.set(false);
                return;
            }

            try {
                const data = JSON.parse(event.data);
                if (data.chunk) {
                    // Update the last message (assistant) with new content
                    this.messages.update(msgs => {
                        const updated = [...msgs];
                        const lastMsg = updated[updated.length - 1];
                        if (lastMsg && lastMsg.role === 'assistant') {
                            lastMsg.content += data.chunk;
                        }
                        return updated;
                    });
                }
            } catch {
                // Handle plain text chunks
                this.messages.update(msgs => {
                    const updated = [...msgs];
                    const lastMsg = updated[updated.length - 1];
                    if (lastMsg && lastMsg.role === 'assistant') {
                        lastMsg.content += event.data;
                    }
                    return updated;
                });
            }
        };

        eventSource.onerror = (error) => {
            console.error('Stream error:', error);
            eventSource.close();
            this.messages.update(msgs => {
                const updated = [...msgs];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
                    lastMsg.content = 'Error: Stream connection failed';
                    lastMsg.isError = true;
                    lastMsg.errorDetails = JSON.stringify(error, null, 2);
                }
                return updated;
            });
            this.isLoading.set(false);
        };
    }

    compareModels(prompt: string, models: string[]): Observable<CompareResponse> {
        return this.http.post<CompareResponse>(`${this.apiUrl}/compare`, {
            prompt,
            models,
        });
    }

    clearHistory(): void {
        this.messages.set([]);
    }
}

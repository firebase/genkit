import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: Date;
    model?: string;
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
                return of({ response: 'Error: Failed to get response', model, latency_ms: 0 });
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
            },
        ]);
        this.isLoading.set(false);
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

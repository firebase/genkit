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

import { Injectable, signal } from '@angular/core';

// Web Speech API type declarations (not included in standard TypeScript libs)
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognitionInterface extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInterface;
    webkitSpeechRecognition: new () => SpeechRecognitionInterface;
  }
}

@Injectable({
  providedIn: 'root',
})
export class SpeechService {
  private recognition: SpeechRecognitionInterface | null = null;
  private synthesis = window.speechSynthesis;

  isListening = signal(false);
  isSpeaking = signal(false);
  transcript = signal('');

  constructor() {
    this.initRecognition();
  }

  private initRecognition(): void {
    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognitionCtor) {
      this.recognition = new SpeechRecognitionCtor();
      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.recognition.onresult = (event: SpeechRecognitionEvent) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          this.transcript.set(finalTranscript);
        }
      };

      this.recognition.onend = () => {
        this.isListening.set(false);
      };

      this.recognition.onerror = (_event: SpeechRecognitionErrorEvent) => {
        this.isListening.set(false);
      };
    }
  }

  isSupported(): boolean {
    return this.recognition !== null;
  }

  isTTSSupported(): boolean {
    return 'speechSynthesis' in window;
  }

  startListening(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!this.recognition) {
        reject(new Error('Speech recognition not supported'));
        return;
      }

      this.transcript.set('');
      this.isListening.set(true);

      const originalOnEnd = this.recognition.onend;
      this.recognition.onend = () => {
        this.isListening.set(false);
        resolve(this.transcript());
        if (this.recognition) {
          this.recognition.onend = originalOnEnd;
        }
      };

      this.recognition.start();
    });
  }

  stopListening(): void {
    if (this.recognition && this.isListening()) {
      this.recognition.stop();
    }
  }

  speak(text: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.isTTSSupported()) {
        reject(new Error('Text-to-speech not supported'));
        return;
      }

      // Cancel any ongoing speech
      this.synthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onstart = () => this.isSpeaking.set(true);
      utterance.onend = () => {
        this.isSpeaking.set(false);
        resolve();
      };
      utterance.onerror = (event) => {
        this.isSpeaking.set(false);
        reject(event);
      };

      this.synthesis.speak(utterance);
    });
  }

  stopSpeaking(): void {
    this.synthesis.cancel();
    this.isSpeaking.set(false);
  }

  getVoices(): SpeechSynthesisVoice[] {
    return this.synthesis.getVoices();
  }
}

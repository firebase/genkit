/**
 * Copyright 2024 Google LLC
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
 */

import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { streamFlow } from '../utils/flow';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  count: string = '3';
  url: string =
    'http://127.0.0.1:5001/YOUR-PROJECT-ID/us-central1/streamCharacters';
  characters: any = undefined;
  error?: string = undefined;
  loading: boolean = false;

  async callFlow() {
    this.characters = undefined;
    this.error = undefined;
    this.loading = true;
    try {
      const response = streamFlow({
        url: this.url,
        payload: parseInt(this.count),
      });
      for await (const chunk of response.stream()) {
        this.characters = chunk;
      }
      console.log('streamConsumer done', await response.output());
      this.loading = false;
    } catch (e) {
      this.loading = false;
      if ((e as any).cause) {
        this.error = `${(e as any).cause}`;
      } else {
        this.error = `${e}`;
      }
    }
  }
}

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
import { MatButtonModule } from '@angular/material/button';
import { streamFlow } from '../../../utils/flow';

const url = 'http://127.0.0.1:3400/streamCharacters';

@Component({
  selector: 'app-streaming-json',
  standalone: true,
  imports: [FormsModule, CommonModule, MatButtonModule],
  templateUrl: './streaming-json.component.html',
  styleUrl: './streaming-json.component.scss',
})
export class StreamingJSONComponent {
  count: string = '3';
  characters: any = undefined;
  error?: string = undefined;
  loading: boolean = false;

  async callFlow() {
    this.characters = undefined;
    this.error = undefined;
    this.loading = true;
    try {
      const response = streamFlow({
        url,
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

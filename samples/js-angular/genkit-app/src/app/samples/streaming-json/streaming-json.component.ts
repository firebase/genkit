import { Component } from '@angular/core';
import { streamFlow } from '../../../utils/flow';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

const url = 'http://127.0.0.1:3400/streamCharacters';

@Component({
  selector: 'app-streaming-json',
  standalone: true,
  imports: [FormsModule, CommonModule, MatButtonModule],
  templateUrl: './streaming-json.component.html',
  styleUrl: './streaming-json.component.scss'
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

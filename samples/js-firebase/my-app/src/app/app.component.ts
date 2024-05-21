import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { streamFlow } from '../utils/flow';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  count: string = '3';
  url: string = 'http://127.0.0.1:5001/YOUR-PROJECT-ID/us-central1/streamCharacters';
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
      console.log("streamConsumer done", await response.output());  
      this.loading = false;
    } catch(e) {
      this.loading = false;
      if ((e as any).cause) {
        this.error = `${(e as any).cause}`;
      } else {
        this.error = `${e}`;
      }
    }
  }
}

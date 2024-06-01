import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { streamFlow } from '../../../utils/flow';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';

const url = 'http://127.0.0.1:3400/streamToolCalling';

@Component({
  selector: 'app-tool-streaming',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatExpansionModule, MatCardModule, MatProgressBarModule],
  templateUrl: './tool-streaming.component.html',
  styleUrl: './tool-streaming.component.scss',
})
export class ToolStreamingComponent {
  error?: string = undefined;
  loading: boolean = false;
  steps: Record<string, any> = {}
  output: any[] = [];

  async callFlow() {
    this.error = undefined;
    this.loading = true;
    this.output = [];
    this.steps = {}
    try {
      const response = streamFlow({
        url,
      });
      for await (const chunk of response.stream()) {
        console.log(chunk)
        if (chunk.label) {
          if (!this.steps[chunk.label]) {
            if (chunk?.label?.startsWith('model call')) {
              if (chunk?.llmChunk?.content[0]?.text) {
                chunk.text = chunk.llmChunk.content[0].text;
              }
            }
            this.steps[chunk.label] = chunk;
            this.output.push(chunk);
          } else {
            const existing = this.steps[chunk.label];
            if (chunk?.label?.startsWith('model call')) {
              if (chunk?.llmChunk?.content[0]?.text) {
                existing.text += chunk.llmChunk.content[0].text;
              }
            }
            if (chunk?.label?.startsWith('tool') && chunk.toolResponse) {
              existing.toolResponse = chunk.toolResponse;
            }
          }
        }
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

import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import {
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { streamFlow } from '../../../utils/flow';
import { MatDatepickerInputEvent, MatDatepickerModule } from '@angular/material/datepicker';
import { provideNativeDateAdapter } from '@angular/material/core';

const url = 'http://127.0.0.1:3400/chatbotFlow';


interface ToolResponse {
  name: string;
  ref: string;
  output?: unknown;
}

interface InputSchema {
  role: 'user';
  text?: string;
  toolResponse?: ToolResponse;
}

interface ToolRequest {
  name: string;
  ref: string;
  input?: unknown;
}
interface OutputSchema {
  role: 'model';
  text?: string;
  toolRequest?: ToolRequest;
}

@Component({
  selector: 'app-chatbot',
  standalone: true,
  providers: [provideNativeDateAdapter()],
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatDatepickerModule,
  ],
  templateUrl: './chatbot.component.html',
  styleUrl: './chatbot.component.scss',
})
export class ChatbotComponent {
  history: (InputSchema | OutputSchema)[] = [];
  error?: string;
  input?: string;
  loading = false;
  id = Date.now() + '' + Math.floor(Math.random() * 1000000000);

  chatFormControl = new FormControl('', [Validators.required]);

  ask(input?: string) {
    const text = this.chatFormControl.value!.trim();
    if (!text) return;
    this.history.push({ role: 'user', text: text });
    this.chatFormControl.setValue('');
    this.chatFormControl.disable();
    this.callFlow({role: 'user', text});
    this.loading = true;
  }

  async callFlow(input: InputSchema) {
    this.error = undefined;
    this.loading = true;
    try {
      const response = await streamFlow({
        url,
        payload: {
          ...input,
          id: this.id,
        },
      });

      let textBlock: OutputSchema | undefined = undefined;
      for await (const chunk of response.stream()) {
        if (chunk.text) {
          if (!textBlock) {
            textBlock = { role: 'model', text: chunk.text!};
            this.history.push(textBlock);
          } else {
            textBlock.text += chunk.text!;
          }
        }
        if (chunk.toolRequest) {
          this.history.push({
            role: 'model',
            toolRequest: chunk.toolRequest,
          });
        }
      }

      this.loading = false;
      this.chatFormControl.enable();
    } catch (e) {
      this.loading = false;
      this.chatFormControl.enable();
      if ((e as any).cause) {
        this.error = `${(e as any).cause}`;
      } else {
        this.error = `${e}`;
      }
    }
  }

  getWeatherLocation(toolRequest: ToolRequest) {
    return (toolRequest.input as any).location;
  }

  datePicked(toolRequest: ToolRequest, event: MatDatepickerInputEvent<Date>) {
    this.callFlow({role: 'user', toolResponse: {
      name: toolRequest.name,
      ref: toolRequest.ref,
      output: `${event.value}`,
    }});
  }
}

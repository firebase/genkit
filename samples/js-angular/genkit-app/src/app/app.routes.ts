import { Routes } from '@angular/router';
import { StreamingJSONComponent } from './samples/streaming-json/streaming-json.component';
import { HomeComponent } from './home/home.component';
import { ChatbotComponent } from './samples/chatbot/chatbot.component';

export const routes: Routes = [
  {
    path: 'home',
    component: HomeComponent,
  },
  {
    path: 'samples/streaming-json',
    component: StreamingJSONComponent,
  },
  {
    path: 'samples/chatbot',
    component: ChatbotComponent,
  },
  { path: '**', redirectTo: '/home' },
];

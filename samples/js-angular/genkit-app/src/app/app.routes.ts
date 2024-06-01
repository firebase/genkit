import { Routes } from '@angular/router';
import { StreamingJSONComponent } from './samples/streaming-json/streaming-json.component';
import { HomeComponent } from './home/home.component';
import { ToolStreamingComponent } from './samples/tool-streaming/tool-streaming.component';

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
    path: 'samples/tool-streaming',
    component: ToolStreamingComponent,
  },
  { path: '**', redirectTo: '/home' },
];

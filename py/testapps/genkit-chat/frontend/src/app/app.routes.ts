import { Routes } from '@angular/router';

export const routes: Routes = [
    {
        path: '',
        loadComponent: () => import('./features/chat/chat.component').then(m => m.ChatComponent),
    },
    {
        path: 'compare',
        loadComponent: () => import('./features/compare/compare.component').then(m => m.CompareComponent),
    },
    {
        path: 'settings',
        loadComponent: () => import('./features/settings/settings.component').then(m => m.SettingsComponent),
    },
];

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

import { CommonModule } from '@angular/common';
import { Component, inject, type OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatRippleModule } from '@angular/material/core';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from './core/services/auth.service';
import { ChatService } from './core/services/chat.service';
import { CodeCopyService } from './core/services/code-copy.service';
import { LanguageService } from './core/services/language.service';
import { ThemeService } from './core/services/theme.service';

@Component({
  selector: 'app-root',
  imports: [
    CommonModule,
    FormsModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatSidenavModule,
    MatToolbarModule,
    MatIconModule,
    MatButtonModule,
    MatListModule,
    MatTooltipModule,
    MatMenuModule,
    MatDividerModule,
    MatRippleModule,
    TranslateModule,
  ],
  template: `
    <mat-sidenav-container class="app-container">
      <!-- Sidebar -->
      <mat-sidenav #sidenav mode="side" opened [class.collapsed]="!sidenavOpened()">
        <div class="sidenav-content">
          <!-- Logo & Brand -->
          <div class="sidenav-header">
            <button mat-icon-button 
                    (click)="toggleSidenav()" 
                    class="menu-btn" 
                    [attr.aria-label]="sidenavOpened() ? 'Collapse menu' : 'Expand menu'"
                    [matTooltip]="sidenavOpened() ? 'Collapse menu' : 'Expand menu'">
              <mat-icon>menu</mat-icon>
            </button>
            @if (sidenavOpened()) {
              <a routerLink="/" class="logo-link">
                <img src="genkit-logo.png" alt="Genkit" class="logo-img">
                <span class="app-name">Genkit Chat</span>
              </a>
            }
          </div>

          <!-- New Chat Button -->
          <button mat-stroked-button class="new-chat-btn" routerLink="/" (click)="startNewChat()" matRipple [matTooltip]="sidenavOpened() ? '' : ('app.newChat' | translate)" matTooltipPosition="right">
            <mat-icon>add</mat-icon>
            @if (sidenavOpened()) {
              <span>{{ 'app.newChat' | translate }}</span>
            }
          </button>

          <mat-nav-list class="main-nav">
            <a mat-list-item routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}" [matTooltip]="sidenavOpened() ? '' : ('nav.chat' | translate)" matTooltipPosition="right">
              <mat-icon matListItemIcon>chat_bubble_outline</mat-icon>
              @if (sidenavOpened()) {
                <span matListItemTitle>{{ 'nav.chat' | translate }}</span>
              }
            </a>
            <a mat-list-item routerLink="/compare" routerLinkActive="active" [matTooltip]="sidenavOpened() ? '' : ('nav.compare' | translate)" matTooltipPosition="right">
              <mat-icon matListItemIcon>compare_arrows</mat-icon>
              @if (sidenavOpened()) {
                <span matListItemTitle>{{ 'nav.compare' | translate }}</span>
              }
            </a>
          </mat-nav-list>

          <!-- Spacer -->
          <div class="spacer"></div>

          <!-- Footer Navigation -->
          <mat-nav-list class="footer-nav">
            <!-- Demo User Toggle -->
            <button mat-list-item (click)="authService.toggleDemoMode()" 
                    [matTooltip]="sidenavOpened() ? '' : ('nav.demoUser' | translate)" 
                    matTooltipPosition="right"
                    [class.demo-active]="authService.demoMode()">
              <mat-icon matListItemIcon>{{ authService.demoMode() ? 'toggle_on' : 'toggle_off' }}</mat-icon>
              @if (sidenavOpened()) {
                <span matListItemTitle>{{ 'nav.demoUser' | translate }}</span>
              }
            </button>
            <a mat-list-item routerLink="/settings" routerLinkActive="active" [matTooltip]="sidenavOpened() ? '' : ('nav.settings' | translate)" matTooltipPosition="right">
              <mat-icon matListItemIcon>settings</mat-icon>
              @if (sidenavOpened()) {
                <span matListItemTitle>{{ 'nav.settings' | translate }}</span>
              }
            </a>
            <button mat-list-item [matMenuTriggerFor]="themeMenu" [matTooltip]="sidenavOpened() ? '' : (('theme.' + themeService.themeMode()) | translate)" matTooltipPosition="right">
              <mat-icon matListItemIcon>{{ themeService.getThemeIcon() }}</mat-icon>
              @if (sidenavOpened()) {
                <span matListItemTitle>{{ 'theme.label' | translate }}: {{ ('theme.' + themeService.themeMode()) | translate }}</span>
              }
            </button>
            <mat-menu #themeMenu="matMenu">
              <button mat-menu-item (click)="themeService.setTheme('system')">
                <mat-icon>brightness_auto</mat-icon>
                <span>{{ 'theme.system' | translate }}</span>
              </button>
              <button mat-menu-item (click)="themeService.setTheme('light')">
                <mat-icon>light_mode</mat-icon>
                <span>{{ 'theme.light' | translate }}</span>
              </button>
              <button mat-menu-item (click)="themeService.setTheme('dark')">
                <mat-icon>dark_mode</mat-icon>
                <span>{{ 'theme.dark' | translate }}</span>
              </button>
            </mat-menu>
            
            <!-- Language Selector -->
            <button mat-list-item [matMenuTriggerFor]="langMenu" [matTooltip]="sidenavOpened() ? '' : languageService.getLanguageLabel()" matTooltipPosition="right">
              <mat-icon matListItemIcon>language</mat-icon>
              @if (sidenavOpened()) {
                <span matListItemTitle>{{ languageService.getLanguageLabel() }}</span>
              }
            </button>
            <mat-menu #langMenu="matMenu" class="language-menu">
              <!-- Filter Input -->
              <div class="lang-filter-container" (click)="$event.stopPropagation()">
                <mat-icon class="filter-icon">search</mat-icon>
                <input type="text" 
                       class="lang-filter-input" 
                       [placeholder]="'language.searchLanguages' | translate"
                       [ngModel]="languageService.languageFilter()"
                       (ngModelChange)="languageService.languageFilter.set($event)"
                       (keydown)="$event.stopPropagation()">
                @if (languageService.languageFilter()) {
                  <button mat-icon-button class="clear-filter-btn" (click)="languageService.languageFilter.set('')">
                    <mat-icon>close</mat-icon>
                  </button>
                }
              </div>
              <mat-divider></mat-divider>
              <button mat-menu-item (click)="languageService.setLanguagePreference('system')">
                <mat-icon>{{ languageService.languagePreference() === 'system' ? 'check' : '' }}</mat-icon>
                <span>{{ 'theme.system' | translate }}</span>
              </button>
              <mat-divider></mat-divider>
              <div class="lang-list-container">
                @for (lang of languageService.filteredLanguages; track lang.code) {
                  <button mat-menu-item class="lang-menu-item" (click)="languageService.setLanguagePreference(lang.code)">
                    <mat-icon class="check-icon" [class.visible]="languageService.languagePreference() === lang.code">check</mat-icon>
                    <span class="lang-flag">{{ lang.flag }}</span>
                    <span class="lang-native-name">{{ lang.nativeName }}</span>
                    <span class="lang-english-name">{{ lang.name }}</span>
                  </button>
                }
                @if (languageService.filteredLanguages.length === 0) {
                  <div class="no-results">{{ 'language.noLanguagesFound' | translate }}</div>
                }
              </div>
            </mat-menu>
          </mat-nav-list>
        </div>
      </mat-sidenav>

      <!-- Main Content Area -->
      <mat-sidenav-content [class.sidebar-collapsed]="!sidenavOpened()">
        <!-- Top Header Bar -->
        <header class="top-bar">
          <div class="top-bar-left">
            <a routerLink="/" class="brand-link">
              <img src="genkit-logo.png" alt="Genkit" class="logo-img small">
            </a>
          </div>
          
          <div class="top-bar-center">
            <span class="app-title">{{ 'app.title' | translate }}</span>
            <span class="version-badge">{{ 'app.version' | translate }}</span>
          </div>
          
          <div class="top-bar-right">
            <button mat-icon-button 
                    [matMenuTriggerFor]="helpMenu" 
                    [attr.aria-label]="'help.label' | translate"
                    [matTooltip]="'help.label' | translate">
              <mat-icon>help_outline</mat-icon>
            </button>
            <mat-menu #helpMenu="matMenu" xPosition="before">
              <a mat-menu-item href="https://firebase.google.com/docs/genkit" target="_blank">
                <mat-icon>menu_book</mat-icon>
                <span>{{ 'help.documentation' | translate }}</span>
              </a>
              <a mat-menu-item href="https://github.com/firebase/genkit" target="_blank">
                <mat-icon>code</mat-icon>
                <span>{{ 'help.github' | translate }}</span>
              </a>
              <mat-divider></mat-divider>
              <button mat-menu-item disabled>
                <mat-icon>info</mat-icon>
                <span>Version 0.1.0</span>
              </button>
            </mat-menu>
            
            <!-- Always show user profile / sign-in in header -->
            @if (authService.user()) {
              <button mat-icon-button [matMenuTriggerFor]="userMenu" [matTooltip]="'auth.account' | translate" class="profile-btn">
                <div class="header-avatar">
                  @if (authService.user()!.picture) {
                    <img [src]="authService.user()!.picture" alt="Profile">
                  } @else {
                    <span>{{ authService.getInitials() }}</span>
                  }
                </div>
              </button>
            } @else {
              <button mat-flat-button color="primary" class="header-signin" (click)="authService.signIn()">
                <mat-icon>login</mat-icon>
                {{ 'auth.signIn' | translate }}
              </button>
            }
          </div>
        </header>

        <!-- User Menu (shared) -->
        <mat-menu #userMenu="matMenu" xPosition="before">
          <div class="user-menu-header" (click)="$event.stopPropagation()">
            <div class="user-menu-avatar">
              @if (authService.user()?.picture) {
                <img [src]="authService.user()!.picture" alt="Profile">
              } @else {
                <span>{{ authService.getInitials() }}</span>
              }
            </div>
            <div class="user-menu-info">
              @if (editingName()) {
                <input class="name-input" 
                       type="text" 
                       [value]="authService.user()?.given_name || ''"
                       (keydown.enter)="saveName($event)"
                       (keydown.escape)="cancelNameEdit()"
                       (blur)="saveName($event)"
                       #nameInput
                       autofocus>
              } @else {
                <span class="name">{{ authService.user()?.given_name || authService.user()?.name }}</span>
              }
              <span class="email">{{ authService.user()?.email }}</span>
            </div>
            <button mat-icon-button class="edit-name-btn" (click)="toggleNameEdit($event)">
              <mat-icon>{{ editingName() ? 'check' : 'edit' }}</mat-icon>
            </button>
          </div>
          <mat-divider></mat-divider>
          <button mat-menu-item disabled>
            <mat-icon>cloud</mat-icon>
            <span>{{ 'auth.connectDrive' | translate }}</span>
          </button>
          <mat-divider></mat-divider>
          <button mat-menu-item (click)="authService.signOut()">
            <mat-icon>logout</mat-icon>
            <span>{{ 'auth.signOut' | translate }}</span>
          </button>
        </mat-menu>

        <!-- Page Content -->
        <main class="main-content">
          <router-outlet />
        </main>
        
        <!-- Footer -->
        <footer class="app-footer">
          <div class="footer-links">
            <a href="https://genkit.dev" target="_blank" rel="noopener">About Genkit</a>
            <span class="separator">·</span>
            <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Privacy</a>
            <span class="separator">·</span>
            <a href="https://policies.google.com/terms" target="_blank" rel="noopener">Terms</a>
            <span class="separator">·</span>
            <a href="https://github.com/firebase/genkit" target="_blank" rel="noopener">GitHub</a>
          </div>
          <div class="copyright">
            © {{ currentYear }} Google LLC. Licensed under Apache 2.0.
          </div>
        </footer>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [
    `
    :host {
      display: block;
      font-family: 'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .app-container {
      height: 100vh;
    }

    /* Sidenav */
    mat-sidenav {
      width: 280px;
      border-right: none !important;
      background: var(--sidebar-bg) !important;
      transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      overflow-x: hidden;
      
      &.collapsed {
        width: 72px;
        
        .sidenav-header {
          justify-content: center;
        }
        
        .new-chat-btn {
          width: 48px;
          min-width: 48px;
          padding: 0 !important;
          justify-content: center;
          
          mat-icon {
            margin: 0;
          }
        }
        
        .mat-mdc-nav-list {
          padding: 4px;
        }
        
        .mat-mdc-list-item {
          padding: 0 !important;
          justify-content: center;
          min-height: 48px;
          width: 48px;
          margin: 2px auto;
          border-radius: 50% !important;
          
          .mdc-list-item__content {
            justify-content: center;
            padding: 0;
          }
          
          mat-icon {
            margin: 0 !important;
          }
        }
      }
    }
    
    mat-sidenav-content {
      display: flex;
      flex-direction: column;
      height: 100vh;
      transition: margin-left 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      background: #ffffff;
      
      &.sidebar-collapsed {
        margin-left: 72px !important;
      }
    }

    .sidenav-content {
      display: flex;
      flex-direction: column;
      height: 100%;
      padding: 12px;
      background: var(--surface-dim);
    }

    .sidenav-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px;
      margin-bottom: 12px;
    }

    .menu-btn {
      flex-shrink: 0;
      
      &:hover {
        background: transparent !important;
        
        mat-icon {
          color: var(--gemini-blue);
        }
      }
    }

    .logo-link {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
    }

    .logo-img {
      height: 36px;
      width: auto;
      opacity: 0.7;
      
      &.dark {
        /* filter: invert(1); removed */
      }
      
      &.small {
        height: 24px;
      }
    }

    .app-name {
      font-size: 16px;
      font-weight: 500;
      color: var(--on-surface);
      letter-spacing: -0.3px;
    }

    .new-chat-btn {
      display: flex;
      align-items: center;
      justify-content: flex-start;
      gap: 12px;
      width: 100%;
      padding: 10px 16px;
      margin-bottom: 8px;
      border-radius: var(--radius-full) !important;
      border-color: var(--surface-variant) !important;
      font-weight: 500;
      
      mat-icon {
        margin: 0;
      }
      
      &:hover {
        background: var(--surface-container);
      }
    }

    .main-nav,
    .footer-nav {
      mat-nav-list,
      .mat-mdc-nav-list {
        padding: 0 !important;
      }
      
      a[mat-list-item], 
      button[mat-list-item] {
        border-radius: var(--radius-full) !important;
        margin: 2px 0;
        height: 40px !important;
        border: none !important;
        background: transparent !important;
        
        // Proper icon/label alignment
        .mdc-list-item__content {
          display: flex !important;
          align-items: center !important;
        }
        
        mat-icon {
          margin-right: 16px !important;
          color: var(--on-surface-variant);
          flex-shrink: 0;
        }
        
        span[matListItemTitle] {
          font-size: 14px;
          font-weight: 400;
        }
        
        &:hover {
          background: var(--surface-container) !important;
        }
        
        &.active {
          background: var(--user-bubble-bg) !important;
          color: var(--gemini-blue-dark) !important;
          
          mat-icon {
            color: var(--gemini-blue-dark) !important;
          }
        }
        
        &.demo-active {
          mat-icon {
            color: #34a853 !important;
          }
        }
      }
    }

    .spacer {
      flex: 1;
    }

    /* User Item in Sidebar */
    .user-item,
    .sign-in-item {
      height: auto !important;
      padding: 8px 16px !important;
    }

    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      overflow: hidden;
      background: var(--gemini-blue);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      
      .avatar-initials {
        color: white;
        font-size: 12px;
        font-weight: 500;
      }
    }

    .user-info {
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .user-name {
      font-size: 14px;
      font-weight: 500;
      color: var(--on-surface);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .user-email {
      font-size: 12px;
      color: var(--on-surface-variant);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Top Bar */
    .top-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 56px;
      padding: 0 12px;
      border-bottom: 1px solid var(--surface-variant);
      background: var(--surface);
    }

    .top-bar-left,
    .top-bar-right {
      display: flex;
      align-items: center;
      gap: 4px;
      min-width: 120px;
    }

    .top-bar-right {
      justify-content: flex-end;
    }

    .mobile-logo {
      display: flex;
      align-items: center;
    }

    .top-bar-center {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .app-title {
      font-size: 16px;
      font-weight: 500;
      color: var(--on-surface);
    }

    .version-badge {
      font-size: 10px;
      font-weight: 500;
      text-transform: uppercase;
      padding: 2px 6px;
      background: var(--surface-container);
      color: var(--on-surface-variant);
      border-radius: 4px;
      letter-spacing: 0.02em;
    }

    .header-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      overflow: hidden;
      background: var(--gemini-blue);
      display: flex;
      align-items: center;
      justify-content: center;
      
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      
      span {
        color: white;
        font-size: 12px;
        font-weight: 500;
      }
    }

    .header-signin {
      border-radius: var(--radius-full) !important;
      font-size: 14px;
      padding: 0 16px !important;
      height: 36px;
      
      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 6px;
      }
    }

    .profile-btn {
      margin-left: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 !important;
      width: 40px;
      height: 40px;
    }

    /* User Menu */
    .user-menu-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
    }

    .user-menu-avatar {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      overflow: hidden;
      background: var(--gemini-blue);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      
      span {
        color: white;
        font-size: 18px;
        font-weight: 500;
      }
    }

    .user-menu-info {
      display: flex;
      flex-direction: column;
      overflow: hidden;
      flex: 1;
      
      .name {
        font-size: 15px;
        font-weight: 500;
        color: var(--on-surface);
      }
      
      .name-input {
        font-size: 15px;
        font-weight: 500;
        color: var(--on-surface);
        border: none;
        border-bottom: 2px solid var(--gemini-blue);
        background: transparent;
        padding: 2px 0;
        outline: none;
        width: 100%;
      }
      
      .email {
        font-size: 13px;
        color: var(--on-surface-variant);
      }
    }
    
    .edit-name-btn {
      width: 32px;
      height: 32px;
      flex-shrink: 0;
      
      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
    }

    /* Main Content */
    .main-content {
      flex: 1;
      overflow: hidden;
      background: var(--surface-dim);
    }

    /* Footer */
    .app-footer {
      flex-shrink: 0;
      padding: 12px 24px;
      text-align: center;
      border-top: 1px solid var(--outline-variant);
      background: var(--surface-dim);
    }

    .footer-links {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      flex-wrap: wrap;
      
      a {
        color: var(--on-surface-muted);
        text-decoration: none;
        font-size: 12px;
        
        &:hover {
          color: var(--gemini-blue);
          text-decoration: underline;
        }
      }
      
      .separator {
        color: var(--on-surface-muted);
        opacity: 0.5;
      }
    }

    .copyright {
      font-size: 11px;
      color: var(--on-surface-muted);
      opacity: 0.7;
    }

    /* Responsive */
    /* Responsive Breakpoints */
    
    /* Language Menu Styles */
    ::ng-deep .language-menu {
      min-width: 320px !important;
      max-width: 400px;
    }
    
    .lang-filter-container {
      display: flex;
      align-items: center;
      padding: 8px 16px;
      gap: 8px;
      
      .filter-icon {
        color: var(--on-surface-muted);
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
      
      .lang-filter-input {
        flex: 1;
        border: none;
        background: transparent;
        font-size: 14px;
        color: var(--on-surface);
        outline: none;
        padding: 4px 0;
        
        &::placeholder {
          color: var(--on-surface-muted);
        }
      }
      
      .clear-filter-btn {
        width: 24px !important;
        height: 24px !important;
        padding: 0 !important;
        
        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
        }
      }
    }
    
    .lang-list-container {
      max-height: 350px;
      overflow-y: auto;
    }
    
    ::ng-deep .lang-menu-item {
      display: flex !important;
      align-items: center;
      gap: 16px;
      min-height: 48px;
      padding: 8px 16px !important;
      
      .lang-flag {
        font-size: 20px;
        flex-shrink: 0;
        width: 24px;
        text-align: center;
        margin-right: 8px;
      }
      
      .lang-native-name {
        flex: 1;
        font-weight: 500;
        white-space: nowrap;
      }
      
      .lang-english-name {
        color: var(--on-surface-muted);
        font-size: 13px;
        margin-left: auto;
        text-align: right;
        padding-left: 16px;
      }
      
      .check-icon {
        color: var(--gemini-blue);
        font-size: 18px;
        width: 18px;
        height: 18px;
        flex-shrink: 0;
        margin-right: 8px;
        visibility: hidden;
        
        &.visible {
          visibility: visible;
        }
      }
    }
    
    .no-results {
      padding: 16px;
      text-align: center;
      color: var(--on-surface-muted);
      font-size: 14px;
    }

    /* Mobile (< 480px) */
    @media (max-width: 479px) {
      mat-sidenav {
        width: 85vw; /* Almost full width */
        max-width: 320px;
        position: fixed;
        z-index: 1000;
        height: 100%;
      }
      
      mat-sidenav.collapsed {
        transform: translateX(-100%);
        width: 85vw;
      }
      
      mat-sidenav-content.sidebar-collapsed {
        margin-left: 0 !important;
      }
    }

    /* Tablet (480px - 768px) */
    @media (min-width: 480px) and (max-width: 768px) {
      mat-sidenav {
        width: 100%;
        max-width: 280px;
      }
    }

    /* Laptop (768px - 1024px) */
    @media (min-width: 769px) and (max-width: 1024px) {
      mat-sidenav {
        width: 260px;
      }
    }

    /* Desktop (> 1024px) */
    @media (min-width: 1025px) {
      /* Standard layout */
    }
  `,
  ],
})
export class AppComponent implements OnInit {
  themeService = inject(ThemeService);
  authService = inject(AuthService);
  languageService = inject(LanguageService);
  private chatService = inject(ChatService);
  private codeCopyService = inject(CodeCopyService);
  sidenavOpened = signal(true);
  editingName = signal(false);
  currentYear = new Date().getFullYear();

  ngOnInit(): void {
    this.authService.restoreSession();
    this.codeCopyService.initialize();
  }

  toggleSidenav(): void {
    this.sidenavOpened.update((v) => !v);
  }

  toggleNameEdit(event: Event): void {
    event.stopPropagation();
    if (this.editingName()) {
      // Save was clicked, no-op (handled by blur/enter)
    }
    this.editingName.update((v) => !v);
  }

  saveName(event: Event): void {
    const input = event.target as HTMLInputElement;
    const newName = input.value.trim();
    if (newName) {
      this.authService.updateName(newName);
    }
    this.editingName.set(false);
  }

  cancelNameEdit(): void {
    this.editingName.set(false);
  }

  startNewChat(): void {
    this.chatService.clearHistory();
  }
}

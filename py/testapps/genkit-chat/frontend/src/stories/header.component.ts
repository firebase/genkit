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
import { Component, EventEmitter, Input, Output } from '@angular/core';

import { ButtonComponent } from './button.component';
import type { User } from './user';

@Component({
  selector: 'storybook-header',
  standalone: true,
  imports: [CommonModule, ButtonComponent],
  template: `<header>
  <div class="storybook-header">
    <div>
      <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <g fill="none" fillRule="evenodd">
          <path
            d="M10 0h12a10 10 0 0110 10v12a10 10 0 01-10 10H10A10 10 0 010 22V10A10 10 0 0110 0z"
            fill="#FFF"
          />
          <path
            d="M5.3 10.6l10.4 6v11.1l-10.4-6v-11zm11.4-6.2l9.7 5.5-9.7 5.6V4.4z"
            fill="#555AB9"
          />
          <path d="M27.2 10.6v11.2l-10.5 6V16.5l10.5-6zM15.7 4.4v11L6 10l9.7-5.5z" fill="#91BAF8" />
        </g>
      </svg>
      <h1>Acme</h1>
    </div>
    <div>
      <div *ngIf="user">
        <span class="welcome">
          Welcome, <b>{{ user.name }}</b
          >!
        </span>
        <storybook-button
          *ngIf="user"
          size="small"
          (onClick)="onLogout.emit($event)"
          label="Log out"
        ></storybook-button>
      </div>
      <div *ngIf="!user">
        <storybook-button
          *ngIf="!user"
          size="small"
          class="margin-left"
          (onClick)="onLogin.emit($event)"
          label="Log in"
        ></storybook-button>
        <storybook-button
          *ngIf="!user"
          size="small"
          [primary]="true"
          class="margin-left"
          (onClick)="onCreateAccount.emit($event)"
          label="Sign up"
        ></storybook-button>
      </div>
    </div>
  </div>
</header>`,
  styleUrls: ['./header.css'],
})
export class HeaderComponent {
  @Input()
  user: User | null = null;

  @Output()
  onLogin = new EventEmitter<Event>();

  @Output()
  onLogout = new EventEmitter<Event>();

  @Output()
  onCreateAccount = new EventEmitter<Event>();
}

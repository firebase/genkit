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
import { Component, Inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

@Component({
  selector: 'app-error-details-dialog',
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule, MatSnackBarModule],
  template: `
    <div class="error-dialog">
      <div class="dialog-header">
        <div class="header-content">
          <mat-icon class="error-icon">error_outline</mat-icon>
          <h2>Error Details</h2>
        </div>
        <button mat-icon-button (click)="dialogRef.close()" class="close-btn">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <div class="dialog-content">
        <div class="code-container">
          <div class="code-header">
            <span class="language-label">JSON</span>
            <button mat-button class="copy-btn" (click)="copyToClipboard()">
              <mat-icon>{{ copied() ? 'check' : 'content_copy' }}</mat-icon>
              {{ copied() ? 'Copied!' : 'Copy' }}
            </button>
          </div>
          <pre class="code-block"><code [innerHTML]="highlightedJson"></code></pre>
        </div>
      </div>

      <div class="dialog-actions">
        <button mat-button (click)="dialogRef.close()">Close</button>
        <button mat-raised-button color="primary" (click)="copyToClipboard()">
          <mat-icon>content_copy</mat-icon>
          Copy to Clipboard
        </button>
      </div>
    </div>
  `,
  styles: [
    `
    :host {
      display: block;
      font-family: 'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    .error-dialog {
      min-width: 500px;
      max-width: 800px;
    }

    .dialog-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 24px;
      border-bottom: 1px solid var(--surface-variant);

      .header-content {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .error-icon {
        color: #d93025;
        font-size: 28px;
        width: 28px;
        height: 28px;
      }

      h2 {
        margin: 0;
        font-size: 20px;
        font-weight: 500;
        color: var(--on-surface);
      }

      .close-btn {
        color: var(--on-surface-muted);
      }
    }

    .dialog-content {
      padding: 24px;
      max-height: 60vh;
      overflow-y: auto;
    }

    .code-container {
      border: 1px solid var(--surface-variant);
      border-radius: 8px;
      overflow: hidden;
    }

    .code-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      background: var(--surface-container);
      border-bottom: 1px solid var(--surface-variant);

      .language-label {
        font-size: 12px;
        font-weight: 500;
        color: var(--on-surface-muted);
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }

      .copy-btn {
        font-size: 12px;
        padding: 4px 8px;
        min-width: auto;
        line-height: 1.2;

        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
          margin-right: 4px;
        }
      }
    }

    .code-block {
      margin: 0;
      padding: 16px;
      background: #1e1e1e;
      color: #d4d4d4;
      font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
      font-size: 13px;
      line-height: 1.6;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;

      /* JSON Syntax Highlighting */
      :host ::ng-deep {
        .json-key {
          color: #9cdcfe;
        }

        .json-string {
          color: #ce9178;
        }

        .json-number {
          color: #b5cea8;
        }

        .json-boolean {
          color: #569cd6;
        }

        .json-null {
          color: #569cd6;
        }

        .json-bracket {
          color: #ffd700;
        }
      }
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      padding: 16px 24px;
      border-top: 1px solid var(--surface-variant);

      button {
        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
          margin-right: 4px;
        }
      }
    }
  `,
  ],
})
export class ErrorDetailsDialogComponent {
  highlightedJson: string;
  copied = signal(false);

  constructor(
    public dialogRef: MatDialogRef<ErrorDetailsDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { errorDetails: string },
    private snackBar: MatSnackBar
  ) {
    this.highlightedJson = this.highlightJson(data.errorDetails);
  }

  private highlightJson(json: string): string {
    let formattedJson = json;
    try {
      // Try to parse and re-format
      const parsed = JSON.parse(json);
      formattedJson = JSON.stringify(parsed, null, 2);
    } catch {
      // Keep original if not valid JSON
    }

    // Syntax highlighting with regex
    return (
      formattedJson
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        // Match JSON keys (strings followed by colon)
        .replace(/"([^"]+)"(?=\s*:)/g, '<span class="json-key">"$1"</span>')
        // Match JSON string values
        .replace(/:\s*"([^"]*)"/g, ': <span class="json-string">"$1"</span>')
        // Match numbers
        .replace(/:\s*(-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
        // Match booleans
        .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
        // Match null
        .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>')
        // Match brackets
        .replace(/([{}[\]])/g, '<span class="json-bracket">$1</span>')
    );
  }

  copyToClipboard(): void {
    navigator.clipboard.writeText(this.data.errorDetails).then(() => {
      this.copied.set(true);
      this.snackBar.open('Copied to clipboard', '', { duration: 2000 });
      setTimeout(() => this.copied.set(false), 2000);
    });
  }
}

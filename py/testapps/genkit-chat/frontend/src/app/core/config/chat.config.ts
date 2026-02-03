// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Chat application configuration constants.
 *
 * These values can be adjusted to customize the chat experience.
 */
export const CHAT_CONFIG = {
  /**
   * Maximum number of file attachments allowed per message.
   */
  maxAttachments: 10,

  /**
   * Maximum file size in bytes (default: 1MB).
   */
  maxFileSizeBytes: 1 * 1024 * 1024,

  /**
   * Allowed file types (MIME type patterns).
   */
  allowedFileTypes: [
    'image/*',
    'video/*',
    'audio/*',
    'application/pdf',
    'text/*',
    'application/json',
    'application/xml',
  ],

  /**
   * Message queue settings.
   */
  queue: {
    maxQueueSize: 50,
    defaultDelay: 500,
  },
} as const;

/**
 * Get Material Icon name for a given MIME type.
 *
 * Uses a hierarchical lookup:
 * 1. Exact MIME type match
 * 2. MIME type category (e.g., image/*, video/*)
 * 3. Fallback to generic file icon
 */
export function getMimeTypeIcon(mimeType: string): string {
  // Exact MIME type matches
  const exactMatches: Record<string, string> = {
    // Documents
    'application/pdf': 'picture_as_pdf',
    'application/msword': 'description',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'description',
    'application/vnd.ms-excel': 'table_chart',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'table_chart',
    'application/vnd.ms-powerpoint': 'slideshow',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'slideshow',

    // Archives
    'application/zip': 'folder_zip',
    'application/x-rar-compressed': 'folder_zip',
    'application/x-7z-compressed': 'folder_zip',
    'application/gzip': 'folder_zip',
    'application/x-tar': 'folder_zip',

    // Data formats
    'application/json': 'data_object',
    'application/xml': 'code',
    'text/xml': 'code',
    'text/html': 'html',
    'text/css': 'css',
    'text/csv': 'table_chart',

    // Code
    'text/javascript': 'javascript',
    'application/javascript': 'javascript',
    'text/x-python': 'code',
    'text/x-java-source': 'code',
    'text/x-c': 'code',
    'text/x-c++': 'code',
    'text/x-go': 'code',
    'text/x-rust': 'code',
    'text/x-typescript': 'code',

    // Markdown
    'text/markdown': 'article',
    'text/x-markdown': 'article',
  };

  // Check exact match first
  if (exactMatches[mimeType]) {
    return exactMatches[mimeType];
  }

  // Category-based matches
  const categoryPrefix = mimeType.split('/')[0];
  const categoryIcons: Record<string, string> = {
    image: 'image',
    video: 'videocam',
    audio: 'audio_file',
    text: 'article',
    font: 'font_download',
    model: 'view_in_ar',
  };

  if (categoryIcons[categoryPrefix]) {
    return categoryIcons[categoryPrefix];
  }

  // Application subtypes that should use specific icons
  if (mimeType.startsWith('application/')) {
    const subtype = mimeType.split('/')[1];

    if (subtype.includes('word') || subtype.includes('document')) {
      return 'description';
    }
    if (subtype.includes('sheet') || subtype.includes('excel')) {
      return 'table_chart';
    }
    if (subtype.includes('presentation') || subtype.includes('powerpoint')) {
      return 'slideshow';
    }
    if (subtype.includes('zip') || subtype.includes('compressed') || subtype.includes('archive')) {
      return 'folder_zip';
    }
  }

  // Default fallback
  return 'insert_drive_file';
}

/**
 * Get a human-readable file type label from a MIME type.
 */
export function getFileTypeLabel(mimeType: string): string {
  const labels: Record<string, string> = {
    'application/pdf': 'PDF',
    'application/json': 'JSON',
    'application/zip': 'ZIP',
    'text/plain': 'Text',
    'text/markdown': 'Markdown',
    'text/csv': 'CSV',
  };

  if (labels[mimeType]) {
    return labels[mimeType];
  }

  const category = mimeType.split('/')[0];
  const capitalizedCategory = category.charAt(0).toUpperCase() + category.slice(1);

  return capitalizedCategory;
}

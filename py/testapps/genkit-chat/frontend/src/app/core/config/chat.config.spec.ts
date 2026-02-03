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

import { describe, expect, it } from 'vitest';
import { CHAT_CONFIG, getFileTypeLabel, getMimeTypeIcon } from './chat.config';

describe('CHAT_CONFIG', () => {
  describe('constants', () => {
    it('should have maxAttachments defined', () => {
      expect(CHAT_CONFIG.maxAttachments).toBe(10);
    });

    it('should have maxFileSizeBytes set to 1MB', () => {
      expect(CHAT_CONFIG.maxFileSizeBytes).toBe(1024 * 1024);
    });

    it('should have allowed file types', () => {
      expect(CHAT_CONFIG.allowedFileTypes).toContain('image/*');
      expect(CHAT_CONFIG.allowedFileTypes).toContain('application/pdf');
      expect(CHAT_CONFIG.allowedFileTypes).toContain('text/*');
    });

    it('should have queue settings', () => {
      expect(CHAT_CONFIG.queue.maxQueueSize).toBe(50);
      expect(CHAT_CONFIG.queue.defaultDelay).toBe(500);
    });
  });
});

describe('getMimeTypeIcon', () => {
  describe('exact MIME type matches', () => {
    it('should return picture_as_pdf for PDF', () => {
      expect(getMimeTypeIcon('application/pdf')).toBe('picture_as_pdf');
    });

    it('should return description for Word documents', () => {
      expect(getMimeTypeIcon('application/msword')).toBe('description');
      expect(
        getMimeTypeIcon('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
      ).toBe('description');
    });

    it('should return table_chart for Excel files', () => {
      expect(getMimeTypeIcon('application/vnd.ms-excel')).toBe('table_chart');
      expect(
        getMimeTypeIcon('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
      ).toBe('table_chart');
    });

    it('should return slideshow for PowerPoint files', () => {
      expect(getMimeTypeIcon('application/vnd.ms-powerpoint')).toBe('slideshow');
      expect(
        getMimeTypeIcon('application/vnd.openxmlformats-officedocument.presentationml.presentation')
      ).toBe('slideshow');
    });

    it('should return folder_zip for archive files', () => {
      expect(getMimeTypeIcon('application/zip')).toBe('folder_zip');
      expect(getMimeTypeIcon('application/x-rar-compressed')).toBe('folder_zip');
      expect(getMimeTypeIcon('application/x-7z-compressed')).toBe('folder_zip');
      expect(getMimeTypeIcon('application/gzip')).toBe('folder_zip');
    });

    it('should return data_object for JSON', () => {
      expect(getMimeTypeIcon('application/json')).toBe('data_object');
    });

    it('should return code for XML', () => {
      expect(getMimeTypeIcon('application/xml')).toBe('code');
      expect(getMimeTypeIcon('text/xml')).toBe('code');
    });

    it('should return article for Markdown', () => {
      expect(getMimeTypeIcon('text/markdown')).toBe('article');
      expect(getMimeTypeIcon('text/x-markdown')).toBe('article');
    });

    it('should return table_chart for CSV', () => {
      expect(getMimeTypeIcon('text/csv')).toBe('table_chart');
    });

    it('should return javascript for JavaScript files', () => {
      expect(getMimeTypeIcon('text/javascript')).toBe('javascript');
      expect(getMimeTypeIcon('application/javascript')).toBe('javascript');
    });

    it('should return code for programming languages', () => {
      expect(getMimeTypeIcon('text/x-python')).toBe('code');
      expect(getMimeTypeIcon('text/x-java-source')).toBe('code');
      expect(getMimeTypeIcon('text/x-c')).toBe('code');
      expect(getMimeTypeIcon('text/x-c++')).toBe('code');
      expect(getMimeTypeIcon('text/x-go')).toBe('code');
      expect(getMimeTypeIcon('text/x-rust')).toBe('code');
      expect(getMimeTypeIcon('text/x-typescript')).toBe('code');
    });
  });

  describe('category-based matches', () => {
    it('should return image for image types', () => {
      expect(getMimeTypeIcon('image/png')).toBe('image');
      expect(getMimeTypeIcon('image/jpeg')).toBe('image');
      expect(getMimeTypeIcon('image/gif')).toBe('image');
      expect(getMimeTypeIcon('image/webp')).toBe('image');
    });

    it('should return videocam for video types', () => {
      expect(getMimeTypeIcon('video/mp4')).toBe('videocam');
      expect(getMimeTypeIcon('video/webm')).toBe('videocam');
      expect(getMimeTypeIcon('video/quicktime')).toBe('videocam');
    });

    it('should return audio_file for audio types', () => {
      expect(getMimeTypeIcon('audio/mpeg')).toBe('audio_file');
      expect(getMimeTypeIcon('audio/wav')).toBe('audio_file');
      expect(getMimeTypeIcon('audio/ogg')).toBe('audio_file');
    });

    it('should return article for text types', () => {
      expect(getMimeTypeIcon('text/plain')).toBe('article');
    });

    it('should return font_download for font types', () => {
      expect(getMimeTypeIcon('font/woff')).toBe('font_download');
      expect(getMimeTypeIcon('font/woff2')).toBe('font_download');
    });

    it('should return view_in_ar for model types', () => {
      expect(getMimeTypeIcon('model/gltf+json')).toBe('view_in_ar');
      expect(getMimeTypeIcon('model/obj')).toBe('view_in_ar');
    });
  });

  describe('application subtype inference', () => {
    it('should return description for word-like documents', () => {
      expect(getMimeTypeIcon('application/x-word')).toBe('description');
    });

    it('should return table_chart for sheet-like files', () => {
      expect(getMimeTypeIcon('application/x-sheet')).toBe('table_chart');
    });

    it('should return slideshow for presentation-like files', () => {
      expect(getMimeTypeIcon('application/x-presentation')).toBe('slideshow');
    });

    it('should return folder_zip for compressed files', () => {
      expect(getMimeTypeIcon('application/x-compressed-anything')).toBe('folder_zip');
    });
  });

  describe('fallback', () => {
    it('should return insert_drive_file for unknown types', () => {
      expect(getMimeTypeIcon('application/octet-stream')).toBe('insert_drive_file');
      expect(getMimeTypeIcon('unknown/type')).toBe('insert_drive_file');
    });
  });
});

describe('getFileTypeLabel', () => {
  describe('exact matches', () => {
    it('should return PDF for application/pdf', () => {
      expect(getFileTypeLabel('application/pdf')).toBe('PDF');
    });

    it('should return JSON for application/json', () => {
      expect(getFileTypeLabel('application/json')).toBe('JSON');
    });

    it('should return ZIP for application/zip', () => {
      expect(getFileTypeLabel('application/zip')).toBe('ZIP');
    });

    it('should return Text for text/plain', () => {
      expect(getFileTypeLabel('text/plain')).toBe('Text');
    });

    it('should return Markdown for text/markdown', () => {
      expect(getFileTypeLabel('text/markdown')).toBe('Markdown');
    });

    it('should return CSV for text/csv', () => {
      expect(getFileTypeLabel('text/csv')).toBe('CSV');
    });
  });

  describe('category fallback', () => {
    it('should capitalize category for image types', () => {
      expect(getFileTypeLabel('image/png')).toBe('Image');
    });

    it('should capitalize category for video types', () => {
      expect(getFileTypeLabel('video/mp4')).toBe('Video');
    });

    it('should capitalize category for audio types', () => {
      expect(getFileTypeLabel('audio/mpeg')).toBe('Audio');
    });

    it('should capitalize category for application types', () => {
      expect(getFileTypeLabel('application/octet-stream')).toBe('Application');
    });
  });
});

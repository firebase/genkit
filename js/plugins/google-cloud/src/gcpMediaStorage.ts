/**
 * Copyright 2024 Google LLC
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
 */

import { Storage } from '@google-cloud/storage';
import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import { createHash } from 'crypto';
import { GenerateRequestData, GenerateResponseData, Part } from 'genkit';
import { logger } from 'genkit/logging';

const SEVEN_DAYS_MS = 7 * 24 * 60 * 60_000;

export class GcpMediaStorage {
  private storage: Storage;
  private readonly bucketName: string;

  constructor(bucketName: string, projectId?: string) {
    this.bucketName = bucketName;
    this.storage = projectId
      ? new Storage({ projectId: projectId })
      : new Storage();
  }

  /**
   * Any message part with a data url in a media part will be uploaded to the configured
   * GCS bucket and the data url will be rewritten to a signed https url pointing to
   * the uploaded object.
   */
  async uploadMedia(spans: ReadableSpan[]): Promise<ReadableSpan[]> {
    return Promise.all(
      spans.map(async (span) => {
        const attributes = span.attributes;
        if (!Object.keys(attributes).includes('genkit:type')) {
          return span; // Not a genkit span
        }
        const type = attributes['genkit:type'] as string;
        const subtype = attributes['genkit:metadata:subtype'] as string;
        if (type === 'action' || subtype === 'model') {
          return await this.uploadMediaParts(span);
        } else {
          return span; // Not a model span
        }
      })
    );
  }

  private async uploadMediaParts(span: ReadableSpan): Promise<ReadableSpan> {
    const attributes = span.attributes;
    let input =
      'genkit:input' in attributes
        ? (JSON.parse(
            attributes['genkit:input']! as string
          ) as GenerateRequestData)
        : undefined;
    let output =
      'genkit:output' in attributes
        ? (JSON.parse(
            attributes['genkit:output']! as string
          ) as GenerateResponseData)
        : undefined;
    if (input && input.messages) {
      await Promise.all(
        input.messages.map(async (msg) => {
          return await Promise.all(
            msg.content.map((p) => this.persistMediaPart(p))
          );
        })
      );
    }
    if (output && output.message) {
      await Promise.all(
        output.message.content.map((p) => this.persistMediaPart(p))
      );
    }
    attributes['genkit:input'] = JSON.stringify(input);
    attributes['genkit:output'] = JSON.stringify(output);
    return span;
  }

  private async persistMediaPart(part: Part): Promise<void> {
    if (part.media && part.media.url.startsWith('data:')) {
      // Decode the base64 data url
      const splitIdx = part.media.url.indexOf('base64,');
      if (splitIdx < 0) {
        return;
      }
      const base64Content = part.media.url.substring(splitIdx + 7);
      let destFileName = createHash('sha1').update(base64Content).digest('hex');
      const contentType =
        part.media.contentType || part.media.url.substring(5, splitIdx - 1);

      // Upload the media
      const contentBuffer = Buffer.from(base64Content, 'base64');
      logger.debug(
        'Uploading ' +
          destFileName +
          ' Content type ' +
          contentType +
          ' Size ' +
          contentBuffer.byteLength
      );
      const bucket = this.storage.bucket(this.bucketName);
      const file = bucket.file(destFileName);
      await file.save(contentBuffer);
      await file.setMetadata({
        contentType: contentType,
      });
      // Set retention here if policy was defined in config?

      /* This isn't working yet
      // Get a signed link
      const [url] = await this.storage
        .bucket(this.bucketName)
        .file(destFileName)
        .getSignedUrl({
          version: 'v4',
          action: 'read',
          expires: Date.now() + SEVEN_DAYS_MS,
        });
      */
      // This link is only accessible to authenticated users
      const url =
        'https://storage.mtls.cloud.google.com/' +
        this.bucketName +
        '/' +
        destFileName;

      // Rewrite the data url to the signed url
      part.media.url = url;
    }
  }
}

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

import { ReadableSpan } from '@opentelemetry/sdk-trace-base';
import { GenerateRequestData, GenerateResponseData, Part } from 'genkit';
import { logger } from 'genkit/logging';

// TODO: This import style causes problems when running tests
import sharp from 'sharp';

export class MediaResizer {
  constructor(
    private width: number,
    private height: number
  ) {}

  /** All images found in data urls will be resized to small thumbnails. */
  async resizeImages(spans: ReadableSpan[]): Promise<ReadableSpan[]> {
    return Promise.all(
      spans.map(async (span) => {
        const attributes = span.attributes;
        if (!Object.keys(attributes).includes('genkit:type')) {
          return span; // Not a genkit span
        }
        const type = attributes['genkit:type'] as string;
        const subtype = attributes['genkit:metadata:subtype'] as string;
        if (type === 'action' || subtype === 'model') {
          return await this.resizeSpanImages(span);
        } else {
          return span; // Not a model span
        }
      })
    );
  }

  private async resizeSpanImages(span: ReadableSpan): Promise<ReadableSpan> {
    const attributes = span.attributes;
    console.log(
      `OUTPUT LENGTH BEFORE: ${(attributes['genkit:output'] as string).length}`
    );
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

    //TODO: This is causing some issues in reassigning the output to the right place
    const outputMessage = output?.message || output?.candidates?.[0]?.message!;

    if (input && input.messages) {
      await Promise.all(
        input.messages.map(async (msg) => {
          return await Promise.all(
            msg.content.map((p) => this.resizeMediaPart(p))
          );
        })
      );
    }

    if (outputMessage) {
      await Promise.all(
        outputMessage.content.map((p) => this.resizeMediaPart(p))
      );
    }

    attributes['genkit:input'] = JSON.stringify(input);
    attributes['genkit:output'] = JSON.stringify(outputMessage);

    console.log(`OUTPUT LENGTH AFTER: ${attributes['genkit:output'].length}`);
    return span;
  }

  private async resizeMediaPart(part: Part): Promise<void> {
    if (part.media && part.media.url.startsWith('data:')) {
      try {
        const splitIdx = part.media.url.indexOf('base64,');
        if (splitIdx < 0) {
          return;
        }
        const base64Content = part.media.url.substring(splitIdx + 7);
        const contentType =
          part.media.contentType || part.media.url.substring(5, splitIdx - 1);

        if (contentType.startsWith('image')) {
          console.log(`ORIGINAL IMAGE LENGTH: ${base64Content.length}`);
          const contentBuffer = Buffer.from(base64Content, 'base64');

          const resizedBuffer = await sharp(contentBuffer)
            .resize(this.width, this.height, { fit: 'contain' })
            .png({ quality: 2, compressionLevel: 9 })
            .toBuffer();

          const url =
            part.media.url.substring(0, splitIdx + 7) +
            resizedBuffer.toString('base64');

          console.log(`RESIZED IMAGE LENGTH: ${url.length}`);

          part.media.url = url;
        }
      } catch (e) {
        logger.error('Could not resize media: \n', e);
        throw e;
      }
    }
  }
}

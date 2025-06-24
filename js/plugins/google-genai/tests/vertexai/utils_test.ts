/**
 * Copyright 2025 Google LLC
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

import * as assert from 'assert';
import { GenerateRequest } from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as sinon from 'sinon';
import { PluginOptions } from '../../src/vertexai/types';
import {
  extractImagenImage,
  extractImagenMask,
  extractText,
  getDerivedOptions,
} from '../../src/vertexai/utils';

describe('getDerivedOptions', () => {
  const originalEnv = { ...process.env };
  let authInstance: sinon.SinonStubbedInstance<GoogleAuth>;
  let mockAuthClass: sinon.SinonStub;

  beforeEach(() => {
    // Reset env
    for (const key in process.env) {
      if (!originalEnv.hasOwnProperty(key)) {
        delete process.env[key];
      }
    }
    for (const key in originalEnv) {
      process.env[key] = originalEnv[key];
    }

    delete process.env.GCLOUD_PROJECT;
    delete process.env.GCLOUD_LOCATION;
    delete process.env.FIREBASE_CONFIG;
    delete process.env.GCLOUD_SERVICE_ACCOUNT_CREDS;

    authInstance = sinon.createStubInstance(GoogleAuth);
    authInstance.getAccessToken.resolves('test-token');

    mockAuthClass = sinon.stub().returns(authInstance);
  });

  afterEach(() => {
    sinon.restore();
  });

  it('should use defaults when no options or env vars are provided', async () => {
    authInstance.getProjectId.resolves('default-project');
    const options = await getDerivedOptions(undefined, mockAuthClass as any);
    assert.strictEqual(options.projectId, 'default-project');
    assert.strictEqual(options.location, 'us-central1');
    assert.ok(options.authClient);
    sinon.assert.calledOnce(mockAuthClass);
    sinon.assert.calledOnce(authInstance.getProjectId);
  });

  it('should use options for projectId and location', async () => {
    const pluginOptions: PluginOptions = {
      projectId: 'options-project',
      location: 'options-location',
    };
    const options = await getDerivedOptions(
      pluginOptions,
      mockAuthClass as any
    );
    assert.strictEqual(options.projectId, 'options-project');
    assert.strictEqual(options.location, 'options-location');
    sinon.assert.calledOnce(mockAuthClass);
    sinon.assert.notCalled(authInstance.getProjectId);
  });

  it('should use GCLOUD_PROJECT and GCLOUD_LOCATION env vars', async () => {
    process.env.GCLOUD_PROJECT = 'env-project';
    process.env.GCLOUD_LOCATION = 'env-location';
    const options = await getDerivedOptions(undefined, mockAuthClass as any);
    assert.strictEqual(options.projectId, 'env-project');
    assert.strictEqual(options.location, 'env-location');
    sinon.assert.calledOnce(mockAuthClass);
    const authOptions = mockAuthClass.lastCall.args[0];
    assert.strictEqual(authOptions.projectId, 'env-project');
    sinon.assert.notCalled(authInstance.getProjectId);
  });

  it('should use FIREBASE_CONFIG for GoogleAuth constructor, but final projectId from getProjectId', async () => {
    process.env.FIREBASE_CONFIG = JSON.stringify({
      projectId: 'firebase-project',
    });
    // This will be called because options.projectId and GCLOUD_PROJECT are missing
    authInstance.getProjectId.resolves('auth-client-project');

    const options = await getDerivedOptions(undefined, mockAuthClass as any);

    // Assert that the constructor received the project ID from FIREBASE_CONFIG
    sinon.assert.calledOnce(mockAuthClass);
    const authOptions = mockAuthClass.lastCall.args[0];
    assert.strictEqual(authOptions.projectId, 'firebase-project');

    // Assert that getProjectId was called to determine the final projectId
    sinon.assert.calledOnce(authInstance.getProjectId);
    assert.strictEqual(options.projectId, 'auth-client-project'); // Final ID is from getProjectId
    assert.strictEqual(options.location, 'us-central1');
  });

  it('should prioritize options over env vars', async () => {
    process.env.GCLOUD_PROJECT = 'env-project';
    process.env.GCLOUD_LOCATION = 'env-location';
    const pluginOptions: PluginOptions = {
      projectId: 'options-project',
      location: 'options-location',
    };
    const options = await getDerivedOptions(
      pluginOptions,
      mockAuthClass as any
    );
    assert.strictEqual(options.projectId, 'options-project');
    assert.strictEqual(options.location, 'options-location');
  });

  it('should use GCLOUD_SERVICE_ACCOUNT_CREDS', async () => {
    const creds = {
      client_email: '<REDACTED_EMAIL>',
      private_key: 'private_key',
    };
    process.env.GCLOUD_SERVICE_ACCOUNT_CREDS = JSON.stringify(creds);
    authInstance.getProjectId.resolves('creds-project');

    const options = await getDerivedOptions(
      { location: 'creds-location' },
      mockAuthClass as any
    );

    assert.strictEqual(options.projectId, 'creds-project');
    assert.strictEqual(options.location, 'creds-location');
    sinon.assert.calledOnce(mockAuthClass);
    const authOptions = mockAuthClass.lastCall.args[0];
    assert.deepStrictEqual(authOptions.credentials, creds);
    assert.strictEqual(authOptions.projectId, undefined);
    sinon.assert.calledOnce(authInstance.getProjectId);
  });

  it('should throw error if projectId cannot be determined', async () => {
    authInstance.getProjectId.resolves(undefined);
    await assert.rejects(
      getDerivedOptions({ location: 'some-location' }, mockAuthClass as any),
      /VertexAI Plugin is missing the 'project' configuration/
    );
    sinon.assert.calledOnce(mockAuthClass);
    sinon.assert.calledOnce(authInstance.getProjectId);
  });
});

describe('extractText', () => {
  it('should extract text from the last message', () => {
    const request: GenerateRequest = {
      messages: [
        { role: 'user', content: [{ text: 'ignore this' }] },
        { role: 'user', content: [{ text: 'Hello ' }, { text: 'World' }] },
      ],
    };
    assert.strictEqual(extractText(request), 'Hello World');
  });

  it('should return empty string if last message has no text parts', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [{ media: { url: 'data:image/png;base64,abc' } }],
        },
      ],
    };
    assert.strictEqual(extractText(request), '');
  });

  it('should handle messages with mixed content', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            { text: 'A ' },
            { media: { url: 'data:image/png;base64,abc' } },
            { text: 'B' },
          ],
        },
      ],
    };
    assert.strictEqual(extractText(request), 'A B');
  });

  it('should return empty string for empty content array', () => {
    const request: GenerateRequest = {
      messages: [{ role: 'user', content: [] }],
    };
    assert.strictEqual(extractText(request), '');
  });
});

describe('extractImagenImage', () => {
  it('should extract base image from last message', () => {
    const request: GenerateRequest = {
      messages: [
        { role: 'user', content: [{ text: 'test' }] },
        {
          role: 'user',
          content: [
            { text: 'An image' },
            {
              media: {
                url: 'data:image/jpeg;base64,base64imagedata',
                contentType: 'image/jpeg',
              },
              metadata: { type: 'base' },
            },
          ],
        },
      ],
    };
    assert.deepStrictEqual(extractImagenImage(request), {
      bytesBase64Encoded: 'base64imagedata',
    });
  });

  it('should extract image if metadata type is missing', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            {
              media: {
                url: 'data:image/png;base64,anotherimage',
                contentType: 'image/png',
              },
            },
          ],
        },
      ],
    };
    assert.deepStrictEqual(extractImagenImage(request), {
      bytesBase64Encoded: 'anotherimage',
    });
  });

  it('should ignore images with metadata type mask', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            {
              media: { url: 'data:image/png;base64,maskdata' },
              metadata: { type: 'mask' },
            },
          ],
        },
      ],
    };
    assert.strictEqual(extractImagenImage(request), undefined);
  });

  it('should return undefined if no media in last message', () => {
    const request: GenerateRequest = {
      messages: [{ role: 'user', content: [{ text: 'No image here' }] }],
    };
    assert.strictEqual(extractImagenImage(request), undefined);
  });

  it('should return undefined if media url is not base64 data URL', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [{ media: { url: 'http://example.com/image.png' } }],
        },
      ],
    };
    assert.strictEqual(extractImagenImage(request), undefined);
  });

  it('should return undefined for empty messages array', () => {
    const request: GenerateRequest = { messages: [] };
    assert.strictEqual(extractImagenImage(request), undefined);
  });
});

describe('extractImagenMask', () => {
  it('should extract mask image from last message', () => {
    const request: GenerateRequest = {
      messages: [
        { role: 'user', content: [{ text: 'test' }] },
        {
          role: 'user',
          content: [
            { text: 'A mask' },
            {
              media: {
                url: 'data:image/png;base64,maskbytes',
                contentType: 'image/png',
              },
              metadata: { type: 'mask' },
            },
          ],
        },
      ],
    };
    assert.deepStrictEqual(extractImagenMask(request), {
      image: { bytesBase64Encoded: 'maskbytes' },
    });
  });

  it('should ignore images with metadata type base', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            {
              media: { url: 'data:image/jpeg;base64,basedata' },
              metadata: { type: 'base' },
            },
          ],
        },
      ],
    };
    assert.strictEqual(extractImagenMask(request), undefined);
  });

  it('should ignore images with no metadata type', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [{ media: { url: 'data:image/jpeg;base64,imagedata' } }],
        },
      ],
    };
    assert.strictEqual(extractImagenMask(request), undefined);
  });

  it('should return undefined if no media in last message', () => {
    const request: GenerateRequest = {
      messages: [{ role: 'user', content: [{ text: 'No mask here' }] }],
    };
    assert.strictEqual(extractImagenMask(request), undefined);
  });

  it('should return undefined if media url is not base64 data URL', () => {
    const request: GenerateRequest = {
      messages: [
        {
          role: 'user',
          content: [
            {
              media: { url: 'http://example.com/mask.png' },
              metadata: { type: 'mask' },
            },
          ],
        },
      ],
    };
    assert.strictEqual(extractImagenMask(request), undefined);
  });

  it('should return undefined for empty messages array', () => {
    const request: GenerateRequest = { messages: [] };
    assert.strictEqual(extractImagenMask(request), undefined);
  });
});

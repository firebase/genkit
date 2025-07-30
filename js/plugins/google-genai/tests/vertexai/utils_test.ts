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
import { GenkitError } from 'genkit';
import { GenerateRequest } from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as sinon from 'sinon';
import {
  ExpressClientOptions,
  GlobalClientOptions,
  RegionalClientOptions,
  VertexPluginOptions,
} from '../../src/vertexai/types';
import {
  API_KEY_FALSE_ERROR,
  MISSING_API_KEY_ERROR,
  calculateApiKey,
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
    delete process.env.VERTEX_API_KEY;
    delete process.env.GOOGLE_API_KEY;
    delete process.env.GOOGLE_GENAI_API_KEY;

    authInstance = sinon.createStubInstance(GoogleAuth);
    authInstance.getAccessToken.resolves('test-token');
    // Default to simulating project ID not found, tests that need it should override.
    authInstance.getProjectId.resolves(undefined);

    mockAuthClass = sinon.stub().returns(authInstance);
  });

  afterEach(() => {
    sinon.restore();
  });

  describe('Regional Options', () => {
    it('should use options for projectId and location', async () => {
      const pluginOptions: VertexPluginOptions = {
        projectId: 'options-project',
        location: 'options-location',
      };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as RegionalClientOptions;
      assert.strictEqual(options.kind, 'regional');
      assert.strictEqual(options.projectId, 'options-project');
      assert.strictEqual(options.location, 'options-location');
      assert.ok(options.authClient);
      sinon.assert.calledOnce(mockAuthClass);
      sinon.assert.notCalled(authInstance.getProjectId);
    });

    it('should use GCLOUD_PROJECT and GCLOUD_LOCATION env vars', async () => {
      process.env.GCLOUD_PROJECT = 'env-project';
      process.env.GCLOUD_LOCATION = 'env-location';
      const options = (await getDerivedOptions(
        undefined,
        mockAuthClass as any
      )) as RegionalClientOptions;
      assert.strictEqual(options.kind, 'regional');
      assert.strictEqual(options.projectId, 'env-project');
      assert.strictEqual(options.location, 'env-location');
      sinon.assert.calledOnce(mockAuthClass);
      const authOptions = mockAuthClass.lastCall.args[0];
      assert.strictEqual(authOptions.projectId, 'env-project');
      sinon.assert.notCalled(authInstance.getProjectId);
    });

    it('should use default location when only projectId is available', async () => {
      authInstance.getProjectId.resolves('default-project');
      const options = (await getDerivedOptions(
        undefined,
        mockAuthClass as any
      )) as RegionalClientOptions;
      assert.strictEqual(options.kind, 'regional');
      assert.strictEqual(options.projectId, 'default-project');
      assert.strictEqual(options.location, 'us-central1');
      sinon.assert.calledOnce(mockAuthClass);
      sinon.assert.calledOnce(authInstance.getProjectId);
    });

    it('should use FIREBASE_CONFIG for GoogleAuth constructor, but final projectId from getProjectId', async () => {
      process.env.FIREBASE_CONFIG = JSON.stringify({
        projectId: 'firebase-project',
      });
      authInstance.getProjectId.resolves('auth-client-project');

      const options = (await getDerivedOptions(
        { location: 'fb-location' },
        mockAuthClass as any
      )) as RegionalClientOptions;

      assert.strictEqual(options.kind, 'regional');
      sinon.assert.calledOnce(mockAuthClass);
      const authOptions = mockAuthClass.lastCall.args[0];
      assert.strictEqual(authOptions.projectId, 'firebase-project');
      sinon.assert.calledOnce(authInstance.getProjectId);
      assert.strictEqual(options.projectId, 'auth-client-project');
      assert.strictEqual(options.location, 'fb-location');
    });

    it('should prioritize plugin options over env vars', async () => {
      process.env.GCLOUD_PROJECT = 'env-project';
      process.env.GCLOUD_LOCATION = 'env-location';
      const pluginOptions: VertexPluginOptions = {
        projectId: 'options-project',
        location: 'options-location',
      };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as RegionalClientOptions;
      assert.strictEqual(options.kind, 'regional');
      assert.strictEqual(options.projectId, 'options-project');
      assert.strictEqual(options.location, 'options-location');
    });

    it('should use GCLOUD_SERVICE_ACCOUNT_CREDS for auth', async () => {
      const creds = {
        client_email: '<REDACTED_EMAIL>',
        private_key: 'private_key',
      };
      process.env.GCLOUD_SERVICE_ACCOUNT_CREDS = JSON.stringify(creds);
      authInstance.getProjectId.resolves('creds-project');

      const options = (await getDerivedOptions(
        { location: 'creds-location' },
        mockAuthClass as any
      )) as RegionalClientOptions;

      assert.strictEqual(options.kind, 'regional');
      assert.strictEqual(options.projectId, 'creds-project');
      assert.strictEqual(options.location, 'creds-location');
      sinon.assert.calledOnce(mockAuthClass);
      const authOptions = mockAuthClass.lastCall.args[0];
      assert.deepStrictEqual(authOptions.credentials, creds);
      assert.strictEqual(authOptions.projectId, undefined);
      sinon.assert.calledOnce(authInstance.getProjectId);
    });

    it('should throw error if projectId cannot be determined for regional', async () => {
      authInstance.getProjectId.resolves(undefined);
      await assert.rejects(
        getDerivedOptions({ location: 'some-location' }, mockAuthClass as any),
        /VertexAI Plugin is missing the 'project' configuration/
      );
      sinon.assert.calledOnce(mockAuthClass);
      sinon.assert.calledOnce(authInstance.getProjectId);
    });

    it('should prefer regional if location is specified, even with apiKey', async () => {
      const pluginOptions: VertexPluginOptions = {
        location: 'us-central1',
        apiKey: 'test-api-key',
        projectId: 'options-project',
      };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as RegionalClientOptions;
      assert.strictEqual(options.kind, 'regional');
      assert.strictEqual(options.projectId, 'options-project');
      assert.strictEqual(options.location, 'us-central1');
      assert.ok(options.authClient);
      sinon.assert.calledOnce(mockAuthClass);
    });
  });

  describe('Global Options', () => {
    it('should use global options when location is global', async () => {
      const pluginOptions: VertexPluginOptions = {
        location: 'global',
        projectId: 'options-project',
      };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as GlobalClientOptions;
      assert.strictEqual(options.kind, 'global');
      assert.strictEqual(options.location, 'global');
      assert.strictEqual(options.projectId, 'options-project');
      assert.ok(options.authClient);
      sinon.assert.calledOnce(mockAuthClass);
      sinon.assert.notCalled(authInstance.getProjectId);
    });

    it('should use env project for global options', async () => {
      process.env.GCLOUD_PROJECT = 'env-project';
      const pluginOptions: VertexPluginOptions = { location: 'global' };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as GlobalClientOptions;
      assert.strictEqual(options.kind, 'global');
      assert.strictEqual(options.projectId, 'env-project');
      sinon.assert.calledOnce(mockAuthClass);
    });

    it('should use auth project for global options', async () => {
      authInstance.getProjectId.resolves('auth-project');
      const pluginOptions: VertexPluginOptions = { location: 'global' };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as GlobalClientOptions;
      assert.strictEqual(options.kind, 'global');
      assert.strictEqual(options.projectId, 'auth-project');
      sinon.assert.calledOnce(mockAuthClass);
      sinon.assert.calledOnce(authInstance.getProjectId);
    });

    it('should throw error if projectId cannot be determined for global', async () => {
      authInstance.getProjectId.resolves(undefined);
      await assert.rejects(
        getDerivedOptions({ location: 'global' }, mockAuthClass as any),
        /VertexAI Plugin is missing the 'project' configuration/
      );
      sinon.assert.calledOnce(mockAuthClass);
      sinon.assert.calledOnce(authInstance.getProjectId);
    });

    it('should prefer global if location is global, even with apiKey', async () => {
      const pluginOptions: VertexPluginOptions = {
        location: 'global',
        apiKey: 'test-api-key',
        projectId: 'options-project',
      };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as GlobalClientOptions;
      assert.strictEqual(options.kind, 'global');
      assert.strictEqual(options.projectId, 'options-project');
      assert.ok(options.authClient);
      sinon.assert.calledOnce(mockAuthClass);
    });
  });

  describe('Express Options', () => {
    it('should use express options with apiKey in options', async () => {
      const pluginOptions: VertexPluginOptions = { apiKey: 'key1' };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as ExpressClientOptions;
      assert.strictEqual(options.kind, 'express');
      assert.strictEqual(options.apiKey, 'key1');
      sinon.assert.notCalled(mockAuthClass);
    });

    it('should use express options with apiKey false in options', async () => {
      const pluginOptions: VertexPluginOptions = { apiKey: false };
      const options = (await getDerivedOptions(
        pluginOptions,
        mockAuthClass as any
      )) as ExpressClientOptions;
      assert.strictEqual(options.kind, 'express');
      assert.strictEqual(options.apiKey, undefined);
      sinon.assert.notCalled(mockAuthClass);
    });

    it('should use VERTEX_API_KEY env var for express', async () => {
      process.env.VERTEX_API_KEY = 'key2';
      const options = (await getDerivedOptions(
        undefined,
        mockAuthClass as any
      )) as ExpressClientOptions;
      assert.strictEqual(options.kind, 'express');
      assert.strictEqual(options.apiKey, 'key2');
      // mockAuthClass is called during regional/global fallbacks
      sinon.assert.calledTwice(mockAuthClass);
    });

    it('should use GOOGLE_API_KEY env var for express', async () => {
      process.env.GOOGLE_API_KEY = 'key3';
      const options = (await getDerivedOptions(
        undefined,
        mockAuthClass as any
      )) as ExpressClientOptions;
      assert.strictEqual(options.kind, 'express');
      assert.strictEqual(options.apiKey, 'key3');
      // mockAuthClass is called during regional/global fallbacks
      sinon.assert.calledTwice(mockAuthClass);
    });

    it('should prioritize VERTEX_API_KEY over GOOGLE_API_KEY for express', async () => {
      process.env.VERTEX_API_KEY = 'keyV';
      process.env.GOOGLE_API_KEY = 'keyG';
      const options = (await getDerivedOptions(
        undefined,
        mockAuthClass as any
      )) as ExpressClientOptions;
      assert.strictEqual(options.kind, 'express');
      assert.strictEqual(options.apiKey, 'keyV');
      // mockAuthClass is called during regional/global fallbacks
      sinon.assert.calledTwice(mockAuthClass);
    });
  });

  describe('Fallback Determination (No Options)', () => {
    it('should default to regional if project can be determined', async () => {
      authInstance.getProjectId.resolves('fallback-project');
      const options = (await getDerivedOptions(
        undefined,
        mockAuthClass as any
      )) as RegionalClientOptions;
      assert.strictEqual(options.kind, 'regional');
      assert.strictEqual(options.projectId, 'fallback-project');
      assert.strictEqual(options.location, 'us-central1');
      sinon.assert.calledOnce(mockAuthClass);
    });

    it('should fallback to express if regional/global fail and API key env exists', async () => {
      authInstance.getProjectId.resolves(undefined); // Fail regional/global project lookup
      process.env.GOOGLE_API_KEY = 'fallback-api-key';

      const options = (await getDerivedOptions(
        undefined,
        mockAuthClass as any
      )) as ExpressClientOptions;

      assert.strictEqual(options.kind, 'express');
      assert.strictEqual(options.apiKey, 'fallback-api-key');
      // getRegionalDerivedOptions, getGlobalDerivedOptions are called first
      sinon.assert.calledTwice(mockAuthClass);
    });
  });

  describe('Error Scenarios', () => {
    it('should throw error if no options or env vars provide sufficient info', async () => {
      authInstance.getProjectId.resolves(undefined); // Simulate failure to get project ID
      // No API key env vars set

      await assert.rejects(getDerivedOptions(undefined, mockAuthClass as any), {
        name: 'GenkitError',
        status: 'INVALID_ARGUMENT',
        message:
          'INVALID_ARGUMENT: Unable to determine client options. Please set either apiKey or projectId and location',
      });
      // Tries Regional, Global, then Express paths. Regional and Global attempts create AuthClient.
      sinon.assert.calledTwice(mockAuthClass);
    });
  });
});

describe('calculateApiKey', () => {
  const originalEnv = { ...process.env };

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
    delete process.env.VERTEX_API_KEY;
    delete process.env.GOOGLE_API_KEY;
    delete process.env.GOOGLE_GENAI_API_KEY;
  });

  function assertThrowsGenkitError(
    block: () => void,
    expectedError: GenkitError
  ) {
    let caughtError: any;
    try {
      block();
    } catch (e: any) {
      caughtError = e;
    }

    if (!caughtError) {
      assert.fail('Should have thrown an error, but nothing was caught.');
    }

    assert.strictEqual(
      caughtError.name,
      'GenkitError',
      `Caught error is not a GenkitError. Got: ${caughtError.name}, Message: ${caughtError.message}`
    );
    assert.strictEqual(caughtError.status, expectedError.status);
    assert.strictEqual(caughtError.message, expectedError.message);
  }

  it('should use requestApiKey when provided', () => {
    assert.strictEqual(calculateApiKey(undefined, 'reqKey'), 'reqKey');
    assert.strictEqual(calculateApiKey('pluginKey', 'reqKey'), 'reqKey');
    assert.strictEqual(calculateApiKey(false, 'reqKey'), 'reqKey');
  });

  it('should use pluginApiKey if requestApiKey is undefined', () => {
    assert.strictEqual(calculateApiKey('pluginKey', undefined), 'pluginKey');
  });

  it('should use VERTEX_API_KEY from env if keys are undefined', () => {
    process.env.VERTEX_API_KEY = 'vertexEnvKey';
    assert.strictEqual(calculateApiKey(undefined, undefined), 'vertexEnvKey');
  });

  it('should use GOOGLE_API_KEY from env if VERTEX_API_KEY is not set', () => {
    process.env.GOOGLE_API_KEY = 'googleEnvKey';
    assert.strictEqual(calculateApiKey(undefined, undefined), 'googleEnvKey');
  });

  it('should prioritize pluginApiKey over env keys', () => {
    process.env.VERTEX_API_KEY = 'vertexEnvKey';
    assert.strictEqual(calculateApiKey('pluginKey', undefined), 'pluginKey');
  });

  it('should throw MISSING_API_KEY_ERROR if no key is found', () => {
    assert.strictEqual(
      process.env.VERTEX_API_KEY,
      undefined,
      'VERTEX_API_KEY should be undefined'
    );
    assert.strictEqual(
      process.env.GOOGLE_API_KEY,
      undefined,
      'GOOGLE_API_KEY should be undefined'
    );
    assert.strictEqual(
      process.env.GOOGLE_GENAI_API_KEY,
      undefined,
      'GOOGLE_GENAI_API_KEY should be undefined'
    );

    assertThrowsGenkitError(
      () => calculateApiKey(undefined, undefined),
      MISSING_API_KEY_ERROR
    );
  });

  it('should throw API_KEY_FALSE_ERROR if pluginApiKey is false and requestApiKey is undefined', () => {
    assertThrowsGenkitError(
      () => calculateApiKey(false, undefined),
      API_KEY_FALSE_ERROR
    );
  });

  it('should not use env keys if pluginApiKey is false', () => {
    process.env.VERTEX_API_KEY = 'vertexEnvKey';
    assertThrowsGenkitError(
      () => calculateApiKey(false, undefined),
      API_KEY_FALSE_ERROR
    );
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
          content: [
            {
              media: {
                url: 'data:image/png;base64,abc',
                contentType: 'image/png',
              },
            },
          ],
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
            {
              media: {
                url: 'data:image/png;base64,abc',
                contentType: 'image/png',
              },
            },
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
              media: {
                url: 'data:image/png;base64,maskdata',
                contentType: 'image/png',
              },
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
          content: [
            {
              media: {
                url: 'http://example.com/image.png',
                contentType: 'image/png',
              },
            },
          ],
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
              media: {
                url: 'data:image/jpeg;base64,basedata',
                contentType: 'image/jpeg',
              },
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
          content: [
            {
              media: {
                url: 'data:image/jpeg;base64,imagedata',
                contentType: 'image/jpeg',
              },
            },
          ],
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
              media: {
                url: 'http://example.com/mask.png',
                contentType: 'image/png',
              },
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

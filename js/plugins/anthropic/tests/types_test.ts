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
import { z } from 'genkit';
import { describe, it } from 'node:test';
import {
  AnthropicConfigSchema,
  McpServerConfigSchema,
  resolveBetaEnabled,
} from '../src/types.js';

describe('resolveBetaEnabled', () => {
  it('should return true when config.apiVersion is beta', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {
      apiVersion: 'beta',
    };
    assert.strictEqual(resolveBetaEnabled(config, 'stable'), true);
  });

  it('should return true when pluginDefaultApiVersion is beta', () => {
    assert.strictEqual(resolveBetaEnabled(undefined, 'beta'), true);
  });

  it('should return false when config.apiVersion is stable', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {
      apiVersion: 'stable',
    };
    assert.strictEqual(resolveBetaEnabled(config, 'stable'), false);
  });

  it('should return false when both are stable', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {
      apiVersion: 'stable',
    };
    assert.strictEqual(resolveBetaEnabled(config, 'stable'), false);
  });

  it('should return false when neither is specified', () => {
    assert.strictEqual(resolveBetaEnabled(undefined, undefined), false);
  });

  it('should return false when config is undefined and plugin default is stable', () => {
    assert.strictEqual(resolveBetaEnabled(undefined, 'stable'), false);
  });

  it('should prioritize config.apiVersion over pluginDefaultApiVersion (beta over stable)', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {
      apiVersion: 'beta',
    };
    // Even though plugin default is stable, request config should override
    assert.strictEqual(resolveBetaEnabled(config, 'stable'), true);
  });

  it('should prioritize config.apiVersion over pluginDefaultApiVersion (stable over beta)', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {
      apiVersion: 'stable',
    };
    // Request explicitly wants stable, should override plugin default
    assert.strictEqual(resolveBetaEnabled(config, 'beta'), false);
  });

  it('should return false when config is empty object', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {};
    assert.strictEqual(resolveBetaEnabled(config, undefined), false);
  });

  it('should return true when config is empty but plugin default is beta', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {};
    assert.strictEqual(resolveBetaEnabled(config, 'beta'), true);
  });

  it('should handle config with other fields but no apiVersion', () => {
    const config: z.infer<typeof AnthropicConfigSchema> = {
      metadata: { user_id: 'test-user' },
    };
    assert.strictEqual(resolveBetaEnabled(config, 'stable'), false);
    assert.strictEqual(resolveBetaEnabled(config, 'beta'), true);
  });
});

describe('McpServerConfigSchema', () => {
  it('should require HTTPS URL', () => {
    const httpConfig = {
      type: 'url' as const,
      url: 'http://example.com/mcp',
      name: 'test-server',
    };
    const result = McpServerConfigSchema.safeParse(httpConfig);
    assert.strictEqual(result.success, false);
    if (!result.success) {
      assert.ok(
        result.error.issues.some((i) =>
          i.message.includes('HTTPS')
        )
      );
    }
  });

  it('should accept HTTPS URL', () => {
    const httpsConfig = {
      type: 'url' as const,
      url: 'https://example.com/mcp',
      name: 'test-server',
    };
    const result = McpServerConfigSchema.safeParse(httpsConfig);
    assert.strictEqual(result.success, true);
  });
});

describe('AnthropicConfigSchema MCP validation', () => {
  it('should fail when server is not referenced by any toolset', () => {
    const config = {
      mcp_servers: [
        {
          type: 'url' as const,
          url: 'https://example.com/mcp',
          name: 'orphan-server',
        },
      ],
      // No mcp_toolsets
    };
    const result = AnthropicConfigSchema.safeParse(config);
    assert.strictEqual(result.success, false);
    if (!result.success) {
      assert.ok(
        result.error.issues.some((i) =>
          i.message.includes('not referenced by any toolset')
        )
      );
    }
  });

  it('should fail when server is referenced by multiple toolsets', () => {
    const config = {
      mcp_servers: [
        {
          type: 'url' as const,
          url: 'https://example.com/mcp',
          name: 'multi-ref-server',
        },
      ],
      mcp_toolsets: [
        {
          type: 'mcp_toolset' as const,
          mcp_server_name: 'multi-ref-server',
        },
        {
          type: 'mcp_toolset' as const,
          mcp_server_name: 'multi-ref-server',
        },
      ],
    };
    const result = AnthropicConfigSchema.safeParse(config);
    assert.strictEqual(result.success, false);
    if (!result.success) {
      assert.ok(
        result.error.issues.some((i) =>
          i.message.includes('referenced by 2 toolsets')
        )
      );
    }
  });

  it('should pass when server is referenced by exactly one toolset', () => {
    const config = {
      mcp_servers: [
        {
          type: 'url' as const,
          url: 'https://example.com/mcp',
          name: 'valid-server',
        },
      ],
      mcp_toolsets: [
        {
          type: 'mcp_toolset' as const,
          mcp_server_name: 'valid-server',
        },
      ],
    };
    const result = AnthropicConfigSchema.safeParse(config);
    assert.strictEqual(result.success, true);
  });

  it('should fail when mcp_server names are not unique', () => {
    const config = {
      mcp_servers: [
        {
          type: 'url' as const,
          url: 'https://example.com/mcp1',
          name: 'duplicate-name',
        },
        {
          type: 'url' as const,
          url: 'https://example.com/mcp2',
          name: 'duplicate-name',
        },
      ],
      mcp_toolsets: [
        {
          type: 'mcp_toolset' as const,
          mcp_server_name: 'duplicate-name',
        },
      ],
    };
    const result = AnthropicConfigSchema.safeParse(config);
    assert.strictEqual(result.success, false);
    if (!result.success) {
      assert.ok(
        result.error.issues.some((i) =>
          i.message.includes('must be unique')
        )
      );
    }
  });

  it('should fail when toolset references unknown server', () => {
    const config = {
      mcp_servers: [
        {
          type: 'url' as const,
          url: 'https://example.com/mcp',
          name: 'real-server',
        },
      ],
      mcp_toolsets: [
        {
          type: 'mcp_toolset' as const,
          mcp_server_name: 'real-server',
        },
        {
          type: 'mcp_toolset' as const,
          mcp_server_name: 'unknown-server',
        },
      ],
    };
    const result = AnthropicConfigSchema.safeParse(config);
    assert.strictEqual(result.success, false);
    if (!result.success) {
      assert.ok(
        result.error.issues.some((i) =>
          i.message.includes("unknown server 'unknown-server'")
        )
      );
    }
  });
});

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

import { googleAI } from '@genkit-ai/google-genai';
import { defineMcpHost } from '@genkit-ai/mcp';
import { genkit, z } from 'genkit';
import { logger } from 'genkit/logging';
import path from 'path';
import { clientTransport } from './in-memory-server.js';

// Turn off safety checks for evaluation so that the LLM as an evaluator can
// respond appropriately to potentially harmful content without error.
export const PERMISSIVE_SAFETY_SETTINGS: any = {
  safetySettings: [
    {
      category: 'HARM_CATEGORY_HATE_SPEECH',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_HARASSMENT',
      threshold: 'BLOCK_NONE',
    },
    {
      category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
      threshold: 'BLOCK_NONE',
    },
  ],
};

export const ai = genkit({
  plugins: [googleAI({ experimental_debugTraces: true })],
  model: googleAI.model('gemini-flash-latest'),
});

logger.setLogLevel('debug'); // Set the logging level to debug for detailed output

export const mcpHostv2 = defineMcpHost(ai, {
  name: 'test-mcp-manager',
  multipart: true,
  mcpServers: {
    'git-client': {
      command: 'uvx',
      args: ['mcp-server-git'],
    },
    fs: {
      command: 'npx',
      args: [
        '-y',
        '@modelcontextprotocol/server-filesystem',
        `${process.cwd()}/test-workspace`,
      ],
    },
    everything: {
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-everything'],
    },
    custom: {
      transport: clientTransport,
    },
  },
});

ai.defineFlow('git-commits', async (q) => {
  const { text } = await ai.generate({
    prompt: `summarize last 5 commits in '${path.resolve(process.cwd(), '../../..')}'`,
    tools: await mcpHostv2.getActiveTools(ai),
  });

  return text;
});

ai.defineFlow('get-test-image-from-mcp', async () => {
  const { text } = await ai.generate({
    prompt: `Please use the get_test_image tool from the custom MCP server to get an image and describe what it looks like.`,
    tools: ['test-mcp-manager:tool/custom/get_test_image'],
  });
  return text;
});

ai.defineFlow('dynamic-git-commits', async (q) => {
  const { text } = await ai.generate({
    prompt: `summarize last 5 commits in '${path.resolve(process.cwd(), '../../..')}'`,
    tools: ['test-mcp-manager:tool/*'], // All the tools
  });

  return text;
});

ai.defineFlow('get-file', async (q) => {
  const { text } = await ai.generate({
    prompt: `summarize contexts of hello-world.txt (in '${process.cwd()}/test-workspace')`,
    tools: await mcpHostv2.getActiveTools(ai),
  });

  return text;
});

ai.defineFlow('dynamic-get-file', async (q) => {
  const { text } = await ai.generate({
    prompt: `summarize contexts of hello-world.txt (in '${process.cwd()}/test-workspace')`,
    tools: ['test-mcp-manager:tool/fs/read_file'], // Just this one tool
  });

  return text;
});

ai.defineFlow('dynamic-prefix-tool', async (q) => {
  // When specifying tools you can use a prefix - so
  // test-mcp-manager:tool/fs/read_* or
  // test-mcp-manager:tool/fs/* will use only the tools whose
  // names match the prefix.
  const { text } = await ai.generate({
    prompt: `summarize contexts of hello-world.txt (in '${process.cwd()}/test-workspace')`,
    tools: ['test-mcp-manager:tool/fs/read_*'], // Just read tools from the fs/
  });

  return text;
});

ai.defineFlow('dynamic-disable-enable', async (q) => {
  // This shows that the dap cache is invalidated any time
  // we change something with the mcpHost config.
  const { text: text1 } = await ai.generate({
    prompt: `summarize contexts of hello-world.txt (in '${process.cwd()}/test-workspace')`,
    tools: ['test-mcp-manager:tool/fs/read_file'], // Just this one tool
  });

  // Now disable fs to show that we invalidate the dap cache
  await mcpHostv2.disable('fs');
  let text2: string;
  try {
    // This should fail because the fs/read_file tool is not available
    // after disabling the mcp client providing it.
    const { text } = await ai.generate({
      prompt: `summarize contexts of hello-world.txt (in '${process.cwd()}/test-workspace')`,
      tools: ['test-mcp-manager:tool/fs/read_file'], // Just this one tool
    });
    text2 =
      'ERROR! This should have failed to find the tool but succeeded instead: ' +
      text;
  } catch (e: any) {
    console.error(JSON.stringify(e.detail, null, 2));
    text2 = e.message;
  }

  // If we re-enable the fs it will succeed.
  await mcpHostv2.enable('fs');
  await mcpHostv2.reconnect('fs');
  const { text: text3 } = await ai.generate({
    prompt: `summarize contexts of hello-world.txt (in '${process.cwd()}/test-workspace')`,
    tools: ['test-mcp-manager:tool/fs/read_file'], // Just this one tool
  });
  return (
    'Original: <br/>' +
    text1 +
    '<br/>After Disable: <br/>' +
    text2 +
    '<br/>After Enable: <br/>' +
    text3
  );
});

ai.defineFlow('test-resource', async (q) => {
  const { text } = await ai.generate({
    prompt: [
      { text: 'analyze this: ' },
      { resource: { uri: 'test://static/resource/1' } },
    ],
    resources: await mcpHostv2.getActiveResources(ai),
  });

  return text;
});

ai.defineFlow('dynamic-test-resources', async (q) => {
  const { text } = await ai.generate({
    prompt: [
      { text: 'analyze this: ' },
      { resource: { uri: 'test://static/resource/1' } },
    ],
    resources: ['test-mcp-manager:resource/*'],
  });

  return text;
});

ai.defineFlow('dynamic-test-one-resource', async (q) => {
  const { text } = await ai.generate({
    prompt: [
      { text: 'analyze this: ' },
      { resource: { uri: 'test://static/resource/1' } },
    ],
    resources: ['test-mcp-manager:resource/everything/Resource 1'],
  });

  return text;
});

ai.defineFlow('update-file', async (q) => {
  const { text } = await ai.generate({
    prompt: `Improve hello-world.txt (in '${process.cwd()}/test-workspace') by rewriting the text, making it longer, just do it, use your imagination.`,
    tools: await mcpHostv2.getActiveTools(ai),
  });

  return text;
});

// MCP Controls
export const controlMcp = ai.defineFlow(
  {
    name: 'controlMcp',
    inputSchema: z.object({
      action: z.enum(['RECONNECT', 'ENABLE', 'DISABLE', 'DISCONNECT'] as const),
      clientId: z.string().optional(),
    }),
    outputSchema: z.string(),
  },
  async ({ action, clientId }) => {
    const id = clientId ?? 'git-client';
    switch (action) {
      case 'DISABLE':
        await mcpHostv2.disable(id);
        break;
      case 'DISCONNECT':
        await mcpHostv2.disconnect(id);
        break;
      case 'RECONNECT':
        await mcpHostv2.reconnect(id);
        break;
      case 'ENABLE':
        await mcpHostv2.enable(id);
        break;
    }
    return action;
  }
);

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

/**
 * Typed-context test app: defines an AppContext, creates genkit<AppContext>(),
 * then runs flows and a tool that use typed context and currentContext().
 */

import { genkit, z } from 'genkit';
import { logger } from 'genkit/logging';

logger.setLogLevel('debug');

// ---------------------------------------------------------------------------
// App context type and Genkit instance
// ---------------------------------------------------------------------------

type AppContext = {
  echo: (value: string) => string;
  hello: (name: string) => string;
  userId?: string;
};

const ai = genkit<AppContext>({
  context: {
    echo: (value) => value,
    hello: (name) => `Hello, ${name}!`,
  },
});

// ---------------------------------------------------------------------------
// Flows and tool (context is typed as AppContext & ActionContext)
// ---------------------------------------------------------------------------

const echoFlow = ai.defineFlow(
  {
    name: 'echoWithContext',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input, { context }) => context.echo(input)
);

const greetFlow = ai.defineFlow(
  {
    name: 'greetWithContext',
    inputSchema: z.object({ name: z.string() }),
    outputSchema: z.string(),
  },
  async (input, { context }) => context.hello(input.name)
);

const flowWithCurrentContext = ai.defineFlow(
  {
    name: 'flowUsingCurrentContext',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    const ctx = ai.currentContext();
    const userId = ctx?.userId ?? 'anonymous';
    return `${input} (user: ${userId})`;
  }
);

const getGreetingTool = ai.defineTool(
  {
    name: 'getGreeting',
    description: 'Returns a greeting using the current context',
    inputSchema: z.object({ name: z.string() }),
    outputSchema: z.string(),
  },
  async (input, { context }) => context.hello(input.name)
);

// ---------------------------------------------------------------------------
// Run examples (log output so you can see typed context in action)
// ---------------------------------------------------------------------------

async function main() {
  const echoAction = await ai.registry.lookupAction('/flow/echoWithContext');

  console.log(
    'Echo with default context:',
    (await echoAction.run('foo')).result
  );

  console.log(
    'Echo with overridden context:',
    (
      await echoFlow.run('foo', {
        context: {
          echo: (value: string) => `${value} ${value}`,
          hello: (name: string) => `Hi, ${name}`,
        },
      })
    ).result
  );

  console.log('Greet:', (await greetFlow.run({ name: 'World' })).result);

  console.log(
    'currentContext() without userId:',
    (await flowWithCurrentContext.run('test')).result
  );

  console.log(
    'currentContext() with userId:',
    (
      await flowWithCurrentContext.run('test', {
        context: {
          userId: 'user-123',
          echo: (v: string) => v,
          hello: (n: string) => `Hey ${n}`,
        },
      })
    ).result
  );

  console.log(
    'Tool with typed context:',
    (await getGreetingTool.run({ name: 'Tool User' })).result
  );
}

main().catch(console.error);

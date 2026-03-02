/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */

import { googleAI } from '@genkit-ai/google-genai';
import { genkit, setGenkitRuntimeConfig, z } from 'genkit';
import { FetchTelemetryProvider } from 'genkit/tracing';

setGenkitRuntimeConfig({
  jsonSchemaMode: 'interpret',
  sandboxedRuntime: true,
  telemetry: new FetchTelemetryProvider({
    serverUrl: 'http://localhost:8787',
    realtime: true,
    // Optional: send auth or other headers with trace export requests
    headers: {
      Authorization: 'Bearer some-secret-token-from-env',
    },
  }),
});

const ai = genkit({
  plugins: [
    googleAI(), // Provide the key via the GOOGLE_GENAI_API_KEY environment variable or arg { apiKey: 'yourkey'}
  ],
});

const greetingFlow = ai.defineFlow(
  {
    name: 'greeting',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    const output = await ai.generate({
      model: 'googleai/gemini-2.5-flash',
      prompt: `Return a short snappy funny greeting for ${input}`,
    });

    return output.text;
  }
);

export default {
  async fetch(request): Promise<Response> {
    const url = new URL(request.url);

		const randomId = Math.random().toString(36).substring(2, 15);

    if (url.pathname === '/api/traces' && request.method === 'POST') {
			const token = request.headers.get('Authorization')?.split(' ').at(1);

			if (token !== 'some-secret-token-from-env') {
				return new Response('Unauthorized', { status: 401 });
			}

			const body = await request.json() as any;

			for (const span of Object.values(body.spans as any[])) {
				if (span.attributes['id'] !== randomId) {
					throw new Error('Invalid span id');
				}
			}

			console.log('Received traces: ', body);

      return new Response('OK', { status: 200 });
    }

    if (url.pathname === '/') {
      const name = url.searchParams.get('name') ?? 'Dave';
      const greeting = await greetingFlow(name, {
        telemetryLabels: {
          id: randomId,
        },
        onTraceStart(traceInfo) {
          console.log('Started trace: ', traceInfo);
        },
      });
      return new Response(greeting);
    }

    return new Response('Not found', { status: 404 });
  },
} satisfies ExportedHandler<Env>;

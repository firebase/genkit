// import { embed } from '@genkit-ai/ai/embedder';
// import assert from 'node:assert';
// import { describe, it } from 'node:test';
// import {
//   defineOllamaEmbedder,
//   OllamaEmbeddingConfigSchema,
// } from '../src/embeddings.js'; // Adjust the import path as necessary
// import { OllamaPluginParams } from '../src/index.js'; // Adjust the import path as necessary

// // Mock fetch to simulate API responses
// global.fetch = async (input: RequestInfo | URL, options?: RequestInit) => {
//   const url = typeof input === 'string' ? input : input.toString();

//   if (url.includes('/api/embedding')) {
//     if (options?.body && JSON.stringify(options.body).includes('fail')) {
//       return {
//         ok: false,
//         statusText: 'Internal Server Error',
//         json: async () => ({}),
//       } as Response;
//     }
//     return {
//       ok: true,
//       json: async () => ({
//         embeddings: {
//           values: [0.1, 0.2, 0.3], // Example embedding values
//         },
//       }),
//     } as Response;
//   }

//   throw new Error('Unknown API endpoint');
// };

// describe('defineOllamaEmbedder', () => {
//   const options: OllamaPluginParams = {
//     models: [{ name: 'test-model' }],
//     serverAddress: 'http://localhost:3000',
//   };

//   it('should successfully return embeddings', async () => {
//     const embedder = defineOllamaEmbedder(
//       'test-embedder',
//       'test-model',
//       options
//     );

//     const result = await embed({
//       embedder,
//       content: 'Hello, world!',
//     });
//     assert.deepStrictEqual(result, [0.1, 0.2, 0.3]);
//   });

//   it('should handle API errors correctly', async () => {
//     const embedder = defineOllamaEmbedder(
//       'test-embedder',
//       'test-model',
//       options
//     );

//     await assert.rejects(
//       async () => {
//         await embed({
//           embedder,
//           content: 'fail',
//         });
//       },
//       (error) => {
//         // Check if error is an instance of Error
//         assert(error instanceof Error);

//         assert.strictEqual(
//           error.message,
//           'Error fetching embedding from Ollama: Internal Server Error'
//         );
//         return true;
//       }
//     );
//   });

//   it('should validate the embedding configuration schema', async () => {
//     const validConfig = {
//       modelName: 'test-model',
//       serverAddress: 'http://localhost:3000',
//     };

//     const invalidConfig = {
//       modelName: 123, // Invalid type
//       serverAddress: 'http://localhost:3000',
//     };

//     // Valid configuration should pass
//     assert.doesNotThrow(() => {
//       OllamaEmbeddingConfigSchema.parse(validConfig);
//     });

//     // Invalid configuration should throw
//     assert.throws(() => {
//       OllamaEmbeddingConfigSchema.parse(invalidConfig);
//     });
//   });

//   it('should throw an error if the fetch response is not ok', async () => {
//     const embedder = defineOllamaEmbedder(
//       'test-embedder',
//       'test-model',
//       options
//     );

//     await assert.rejects(async () => {
//       await embed({
//         embedder,
//         content: 'fail',
//       });
//     }, new Error('Error fetching embedding from Ollama: Internal Server Error'));
//   });
// });

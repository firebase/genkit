import { startServer } from './server.js';
import { runClientTest } from './client.js';

async function main() {
  // 1. Start the A2A server
  const server = startServer();
  
  // Wait a bit for server to be ready
  await new Promise((resolve) => setTimeout(resolve, 1000));
  
  try {
    // 2. Run the client test
    console.log('Starting client test...');
    // Flow run takes input directly or via options.
    // In client.ts, inputSchema is z.string()
    const result = await runClientTest('Hello Genkit A2A!');
    console.log('Test completed with result:', result);
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    // Close server to exit
    server.close(() => console.log('Server stopped.'));
  }
}

main();

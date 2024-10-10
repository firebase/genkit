import crypto from 'crypto';

export function generateCacheKey(request: any): string {
  // Select relevant parts of the request to generate a hash (e.g., messages, config)
  const hashInput = JSON.stringify({
    messages: request.messages,
    config: request.config,
    tools: request.tools,
  });

  return crypto.createHash('sha256').update(hashInput).digest('hex');
}

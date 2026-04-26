import {
  AgentExecutor,
  RequestContext,
  ExecutionEventBus,
} from '@a2a-js/sdk/server';
import type {
  Message as A2AMessage,
  Part as A2APart,
  TextPart as A2ATextPart,
  FilePart as A2AFilePart,
  FileWithUri as A2AFileWithUri,
  FileWithBytes as A2AFileWithBytes,
} from '@a2a-js/sdk';
import { ClientFactory } from '@a2a-js/sdk/client';
import { Genkit, Part } from 'genkit';
import { SessionFlow, SessionRunner, SessionFlowStreamChunk, defineSessionFlow } from '@genkit-ai/ai';
import { v4 as uuidv4 } from 'uuid';



interface A2AMessageWithParts extends A2AMessage {
  parts: A2APart[];
}

interface A2AClient {
  sendMessageStream(params: Record<string, unknown>): AsyncIterable<Record<string, unknown>>;
}

interface A2AClientFactory {
  createFromUrl(url: string): Promise<A2AClient>;
}

/**
 * Maps a Genkit Part to an A2A Part.
 */
export function mapGenkitPartToA2A(part: Part): A2APart {
  if (part.text) {
    return { kind: 'text', text: part.text } as A2ATextPart;
  }
  
  if (part.media) {
    const url = part.media.url;
    const mimeType = part.media.contentType;
    
    if (url.startsWith('data:')) {
      const match = url.match(/^data:([^;]+);base64,(.+)$/);
      if (match) {
        return {
          kind: 'file',
          file: {
            bytes: match[2],
            mimeType: match[1] || mimeType,
            name: 'inline_file',
          } as A2AFileWithBytes
        } as A2AFilePart;
      }
    }
    
    return {
      kind: 'file',
      file: {
        uri: url,
        mimeType: mimeType,
        name: 'remote_file',
      } as A2AFileWithUri
    } as A2AFilePart;
  }

  // Fallback for complex parts (like tool calls) to prevent data loss
  return {
    kind: 'text',
    text: JSON.stringify(part),
  } as A2ATextPart;
}

/**
 * Maps an A2A Part to a Genkit Part.
 */
export function mapA2APartToGenkit(part: A2APart): Part {
  if (part.kind === 'text') {
    const textPart = part as A2ATextPart;
    try {
      // Attempt to restore complex parts serialized as JSON
      return JSON.parse(textPart.text);
    } catch {
      return { text: textPart.text };
    }
  }
  
  if (part.kind === 'file') {
    const filePart = part as A2AFilePart;
    const file = filePart.file;
    
    if ('bytes' in file) {
      const bytesFile = file as A2AFileWithBytes;
      return {
        media: {
          url: `data:${bytesFile.mimeType || 'application/octet-stream'};base64,${bytesFile.bytes}`,
          contentType: bytesFile.mimeType,
        }
      };
    } else if ('uri' in file) {
      const uriFile = file as A2AFileWithUri;
      return {
        media: {
          url: uriFile.uri,
          contentType: uriFile.mimeType,
        }
      };
    }
  }
  
  // Fallback
  return { text: JSON.stringify(part) };
}

/**
 * Exposes a Genkit Session Flow as an A2A Agent.
 */
export class SessionFlowAgentExecutor implements AgentExecutor {
  constructor(private sessionFlow: SessionFlow<unknown, unknown>) {}

  async execute(requestContext: RequestContext, eventBus: ExecutionEventBus): Promise<void> {
    const { taskId, contextId, userMessage } = requestContext;

    if (!userMessage) {
      eventBus.finished();
      return;
    }

    // Map A2A message to Genkit input
    const genkitInput = {
      messages: [
        {
          role: 'user' as const,
          content: (userMessage as A2AMessageWithParts).parts.map(mapA2APartToGenkit),
        },
      ],
    };

    try {
      // We use streamBidi to interact with the session flow
      const session = this.sessionFlow.streamBidi({}, {
        init: { snapshotId: contextId },
      });

      // Send the user message
      session.send(genkitInput);
      session.close();

      // Consume the stream and forward to A2A event bus
      for await (const chunk of session.stream) {
        if (chunk.modelChunk?.content) {
          eventBus.publish({
            kind: 'message',
            messageId: uuidv4(),
            role: 'agent',
            parts: chunk.modelChunk.content.map(mapGenkitPartToA2A),
            contextId,
          });
        }

        if (chunk.status) {
          eventBus.publish({
            kind: 'status-update',
            taskId,
            contextId,
            status: { state: chunk.status, timestamp: new Date().toISOString() },
            final: false,
          });
        }

        if (chunk.artifact) {
          const genkitArtifact = chunk.artifact as { name?: string, parts?: Part[] };
          eventBus.publish({
            kind: 'artifact-update',
            taskId,
            contextId,
            artifact: {
              artifactId: genkitArtifact.name || uuidv4(),
              parts: genkitArtifact.parts?.map(mapGenkitPartToA2A) || [],
            },
          });
        }
      }

      // Wait for the final output to ensure state is persisted
      await session.output;
      
    } catch (error: unknown) {
      eventBus.publish({
        kind: 'status-update',
        taskId,
        contextId,
        status: { state: 'failed', timestamp: new Date().toISOString() },
        final: true,
      });
      throw error;
    }

    eventBus.finished();
  }

  async cancelTask(taskId: string, eventBus: ExecutionEventBus): Promise<void> {
    try {
      await this.sessionFlow.abort(taskId);
      eventBus.publish({
        kind: 'status-update',
        taskId,
        contextId: taskId,
        status: { state: 'canceled', timestamp: new Date().toISOString() },
        final: true,
      });
    } catch (e) {
      console.error(`Failed to abort task ${taskId}:`, e);
    }
  }
}

/**
 * Defines a Genkit Session Flow that consumes a remote A2A Agent.
 */
export function defineA2ASessionFlow(
  ai: Genkit,
  config: {
    name: string;
    agentUrl: string;
    description?: string;
    clientFactory?: A2AClientFactory;
  }
) {
  return defineSessionFlow(
    ai.registry,
    {
      name: config.name,
      description: config.description,
    },
    async (sess: SessionRunner<unknown, unknown>, { sendChunk }: { sendChunk: (chunk: SessionFlowStreamChunk<unknown>) => void }) => {
      // Use provided factory or create a new one
      const factory = config.clientFactory || (new ClientFactory() as unknown as A2AClientFactory);
      const client = await factory.createFromUrl(config.agentUrl);

      // Run the turn loop
      await sess.run(async (input) => {
        const userMessage = input.messages?.[input.messages.length - 1];
        if (!userMessage) return;

        // Map Genkit Message to A2A Message
        const a2aParams: { message: A2AMessage } = {
          message: {
            kind: 'message' as const,
            messageId: uuidv4(),
            role: 'user' as const,
            parts: userMessage.content.map(mapGenkitPartToA2A),
          },
        };

        // Consume the A2A stream
        const stream = client.sendMessageStream(a2aParams);
        const responseParts: Part[] = [];

        for await (const event of stream) {
          const recordEvent = event as Record<string, unknown>;
          if (recordEvent.kind === 'message') {
            const a2aEvent = event as { parts: A2APart[] };
            const genkitParts = a2aEvent.parts.map(mapA2APartToGenkit);
            responseParts.push(...genkitParts);
            sendChunk({
              modelChunk: {
                role: 'model',
                content: genkitParts,
              },
            });
          } else if (recordEvent.kind === 'status-update') {
            const statusUpdate = recordEvent as { status: { state: string } };
            sendChunk({ status: statusUpdate.status.state });
          } else if (recordEvent.kind === 'artifact-update') {
            const a2aArtifact = recordEvent.artifact as { artifactId: string, parts: A2APart[] };
            sendChunk({
              artifact: {
                name: a2aArtifact.artifactId,
                parts: a2aArtifact.parts.map(mapA2APartToGenkit),
              }
            });
          }
        }

        // Persist the accumulated response message
        if (responseParts.length > 0) {
          sess.session.addMessages([{ role: 'model', content: responseParts }]);
        }
      });

      const msgs = sess.session.getMessages();
      return {
        message: msgs[msgs.length - 1],
        artifacts: sess.session.getArtifacts(),
      };
    }
  );
}

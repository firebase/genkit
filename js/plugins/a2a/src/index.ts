import {
  AgentExecutor,
  RequestContext,
  ExecutionEventBus,
} from '@a2a-js/sdk/server';
import type {
  Artifact as A2AArtifact,
  Message as A2AMessage,
  Part as A2APart,
  TextPart as A2ATextPart,
  FilePart as A2AFilePart,
  FileWithUri as A2AFileWithUri,
  FileWithBytes as A2AFileWithBytes,
  Task as A2ATask,
  TaskStatusUpdateEvent as A2ATaskStatusUpdateEvent,
  TaskArtifactUpdateEvent as A2ATaskArtifactUpdateEvent,
  MessageSendParams as A2AMessageSendParams,
} from '@a2a-js/sdk';
import { ClientFactory } from '@a2a-js/sdk/client';
import { Genkit, Part } from 'genkit';
import {
  SessionFlow,
  SessionFlowStreamChunk,
  SessionRunner,
  defineSessionFlow,
} from '@genkit-ai/ai';
import { v4 as uuidv4 } from 'uuid';

type Artifact = NonNullable<SessionFlowStreamChunk['artifact']>;

type A2AStreamEventData =
  | A2AMessage
  | A2ATask
  | A2ATaskStatusUpdateEvent
  | A2ATaskArtifactUpdateEvent;

interface A2AClientLike {
  sendMessageStream(params: A2AMessageSendParams): AsyncIterable<A2AStreamEventData>;
}

interface A2AClientFactory {
  createFromUrl(url: string): Promise<A2AClientLike>;
}

/** Known Genkit Part discriminator keys, used to validate JSON-restored parts. */
const GENKIT_PART_KEYS = new Set(['text', 'media', 'toolRequest', 'toolResponse', 'data', 'custom']);

function isGenkitPart(value: unknown): value is Part {
  return (
    value !== null &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    Object.keys(value as object).some((k) => GENKIT_PART_KEYS.has(k))
  );
}

/**
 * Maps a Genkit Part to an A2A Part.
 */
export function mapGenkitPartToA2A(part: Part): A2APart {
  if (part.text !== undefined) {
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
          } as A2AFileWithBytes,
        } as A2AFilePart;
      }
    }

    return {
      kind: 'file',
      file: {
        uri: url,
        mimeType: mimeType,
        name: 'remote_file',
      } as A2AFileWithUri,
    } as A2AFilePart;
  }

  // Fallback for complex parts (toolRequest, toolResponse, etc.)
  return { kind: 'text', text: JSON.stringify(part) } as A2ATextPart;
}

/**
 * Maps an A2A Part to a Genkit Part.
 * Text parts that were serialized as JSON by mapGenkitPartToA2A are restored
 * only when they parse to a valid Genkit Part object.
 */
export function mapA2APartToGenkit(part: A2APart): Part {
  if (part.kind === 'text') {
    const textPart = part as A2ATextPart;
    try {
      const parsed = JSON.parse(textPart.text);
      if (isGenkitPart(parsed)) {
        return parsed;
      }
    } catch {
      // not JSON — fall through to plain text
    }
    return { text: textPart.text };
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
        },
      };
    } else if ('uri' in file) {
      const uriFile = file as A2AFileWithUri;
      return {
        media: {
          url: uriFile.uri,
          contentType: uriFile.mimeType,
        },
      };
    }
  }

  // Fallback
  return { text: JSON.stringify(part) };
}

/**
 * Maps a Genkit Artifact to an A2A Artifact.
 * Artifact.name is required — throws if absent, as it is used as the A2A artifactId.
 * A2A-specific display fields can be supplied via metadata.a2a.{name,description,extensions}.
 */
export function mapGenkitArtifactToA2A(artifact: Artifact): A2AArtifact {
  if (!artifact.name) {
    throw new Error(
      'Artifact.name is required when using the A2A adapter. ' +
        'Set a unique name on each artifact to serve as its A2A artifactId.'
    );
  }

  const { a2a: a2aMeta, ...restMetadata } = (artifact.metadata || {}) as Record<string, any>;
  const a2aOverrides: Record<string, any> = a2aMeta || {};

  return {
    artifactId: artifact.name,
    name: a2aOverrides.name ?? artifact.name,
    ...(a2aOverrides.description !== undefined && { description: a2aOverrides.description }),
    ...(a2aOverrides.extensions !== undefined && { extensions: a2aOverrides.extensions }),
    parts: artifact.parts.map(mapGenkitPartToA2A),
    ...(Object.keys(restMetadata).length > 0 && { metadata: restMetadata }),
  };
}

/**
 * Maps an A2A Artifact to a Genkit Artifact.
 * The A2A artifactId becomes Genkit name (deduplication key).
 * A2A-specific fields (name, description, extensions, metadata) are stored under metadata.a2a.
 */
export function mapA2AArtifactToGenkit(artifact: A2AArtifact): Artifact {
  const a2aMeta: Record<string, unknown> = {};
  if (artifact.name !== undefined) a2aMeta.name = artifact.name;
  if (artifact.description !== undefined) a2aMeta.description = artifact.description;
  if (artifact.extensions !== undefined) a2aMeta.extensions = artifact.extensions;
  if (artifact.metadata !== undefined) a2aMeta.metadata = artifact.metadata;

  return {
    name: artifact.artifactId,
    parts: artifact.parts.map(mapA2APartToGenkit),
    ...(Object.keys(a2aMeta).length > 0 && { metadata: { a2a: a2aMeta } }),
  };
}

/**
 * Exposes a Genkit Session Flow as an A2A Agent.
 *
 * The flow MUST be defined without a session store (client-managed state).
 * The executor acts as the state client: it holds session state per A2A contextId
 * and replays it on each turn via `init.state`.  Server-managed flows (with a store)
 * are not supported because A2A and the Genkit store would conflict over ownership
 * of session state.  Detachment (`detach: true`) is also not supported for the same
 * reason — it requires a server-side store.
 */
export class SessionFlowAgentExecutor implements AgentExecutor {
  /** contextId → full Genkit session state for that conversation */
  private contextStates = new Map<string, Record<string, unknown>>();
  /** taskId → contextId, needed because cancelTask only receives taskId */
  private taskContexts = new Map<string, string>();
  /** taskIds for which cancellation has been requested */
  private cancelledTasks = new Set<string>();

  constructor(private sessionFlow: SessionFlow<unknown, unknown>) {}

  async execute(requestContext: RequestContext, eventBus: ExecutionEventBus): Promise<void> {
    const { taskId, contextId, userMessage } = requestContext;

    if (!userMessage) {
      eventBus.finished();
      return;
    }

    this.taskContexts.set(taskId, contextId);

    if (!requestContext.task) {
      eventBus.publish({
        kind: 'task',
        id: taskId,
        contextId,
        status: { state: 'submitted', timestamp: new Date().toISOString() },
      } as A2ATask);
    }

    eventBus.publish({
      kind: 'status-update',
      taskId,
      contextId,
      status: { state: 'working', timestamp: new Date().toISOString() },
      final: false,
    } as A2ATaskStatusUpdateEvent);

    const genkitInput = {
      messages: [
        {
          role: 'user' as const,
          content: (userMessage as A2AMessage).parts.map(mapA2APartToGenkit),
        },
      ],
    };

    try {
      const existingState = this.contextStates.get(contextId);
      const session = this.sessionFlow.streamBidi(
        existingState ? { state: existingState } : {}
      );

      session.send(genkitInput);
      session.close();

      for await (const chunk of session.stream) {
        if (this.cancelledTasks.has(taskId)) break;

        if (chunk.modelChunk?.content) {
          eventBus.publish({
            kind: 'message',
            messageId: uuidv4(),
            role: 'agent',
            parts: chunk.modelChunk.content.map(mapGenkitPartToA2A),
            contextId,
          } as A2AMessage);
        }

        if (chunk.status) {
          eventBus.publish({
            kind: 'status-update',
            taskId,
            contextId,
            status: { state: chunk.status, timestamp: new Date().toISOString() },
            final: false,
          } as A2ATaskStatusUpdateEvent);
        }

        if (chunk.artifact) {
          eventBus.publish({
            kind: 'artifact-update',
            taskId,
            contextId,
            artifact: mapGenkitArtifactToA2A(chunk.artifact),
          } as A2ATaskArtifactUpdateEvent);
        }
      }

      const output = await session.output;
      if (!output.state) {
        throw new Error(
          `SessionFlowAgentExecutor requires a client-managed state flow (no store). ` +
          `The flow '${(this.sessionFlow as any).__action?.name ?? 'unknown'}' appears to ` +
          `have a session store configured, which is not supported with the A2A adapter.`
        );
      }
      this.contextStates.set(contextId, output.state as Record<string, unknown>);

      eventBus.publish({
        kind: 'status-update',
        taskId,
        contextId,
        status: { state: 'completed', timestamp: new Date().toISOString() },
        final: true,
      } as A2ATaskStatusUpdateEvent);
    } catch (error: unknown) {
      eventBus.publish({
        kind: 'status-update',
        taskId,
        contextId,
        status: { state: 'failed', timestamp: new Date().toISOString() },
        final: true,
      } as A2ATaskStatusUpdateEvent);
      eventBus.finished();
      throw error;
    }

    eventBus.finished();
  }

  async cancelTask(taskId: string, eventBus: ExecutionEventBus): Promise<void> {
    this.cancelledTasks.add(taskId);

    const contextId = this.taskContexts.get(taskId);

    eventBus.publish({
      kind: 'status-update',
      taskId,
      contextId: contextId ?? taskId,
      status: { state: 'canceled', timestamp: new Date().toISOString() },
      final: true,
    } as A2ATaskStatusUpdateEvent);
    eventBus.finished();
  }
}

/**
 * Defines a Genkit Session Flow that consumes a remote A2A Agent.
 * The remote agent client is created once and reused across flow invocations.
 * A stable A2A contextId is generated per Genkit session invocation, ensuring
 * multi-turn conversations are correctly associated on the remote side.
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
  let cachedClient: A2AClientLike | undefined;

  return defineSessionFlow(
    ai.registry,
    {
      name: config.name,
      description: config.description,
    },
    async (
      sess: SessionRunner<unknown, unknown>,
      {
        sendChunk,
      }: { sendChunk: (chunk: SessionFlowStreamChunk<unknown>) => void }
    ) => {
      if (!cachedClient) {
        const factory =
          config.clientFactory ||
          (new ClientFactory() as unknown as A2AClientFactory);
        cachedClient = await factory.createFromUrl(config.agentUrl);
      }

      // One stable A2A contextId for all turns in this Genkit session invocation.
      const a2aContextId = uuidv4();

      await sess.run(async (input) => {
        const userMessage = input.messages?.[input.messages.length - 1];
        if (!userMessage) return;

        const a2aParams: A2AMessageSendParams = {
          message: {
            kind: 'message',
            messageId: uuidv4(),
            role: 'user',
            parts: userMessage.content.map(mapGenkitPartToA2A),
            contextId: a2aContextId,
          },
        };

        const stream = cachedClient!.sendMessageStream(a2aParams);
        const responseParts: Part[] = [];

        for await (const event of stream) {
          if (event.kind === 'message') {
            const genkitParts = event.parts.map(mapA2APartToGenkit);
            responseParts.push(...genkitParts);
            sendChunk({
              modelChunk: {
                role: 'model',
                content: genkitParts,
              },
            });
          } else if (event.kind === 'status-update') {
            sendChunk({ status: event.status.state });
          } else if (event.kind === 'artifact-update') {
            sendChunk({
              artifact: mapA2AArtifactToGenkit(event.artifact as A2AArtifact),
            });
          }
        }

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

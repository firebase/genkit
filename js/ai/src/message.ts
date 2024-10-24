import { extractJson } from './extract';
import { MessageData, Part, ToolRequestPart, ToolResponsePart } from './model';

/**
 * Message represents a single role's contribution to a generation. Each message
 * can contain multiple parts (for example text and an image), and each generation
 * can contain multiple messages.
 */
export class Message<T = unknown> implements MessageData {
  role: MessageData['role'];
  content: Part[];
  metadata?: Record<string, any>;

  static parseData(
    lenientMessage:
      | string
      | (MessageData & { content: string | Part | Part[]; role: string })
      | MessageData,
    defaultRole: MessageData['role'] = 'user'
  ): MessageData {
    if (typeof lenientMessage === 'string') {
      return { role: defaultRole, content: [{ text: lenientMessage }] };
    }
    return {
      ...lenientMessage,
      content: Message.parseContent(lenientMessage.content),
    };
  }

  static parse(
    lenientMessage: string | (MessageData & { content: string }) | MessageData
  ): Message {
    return new Message(Message.parseData(lenientMessage));
  }

  static parseContent(lenientPart: string | Part | (string | Part)[]): Part[] {
    if (typeof lenientPart === 'string') {
      return [{ text: lenientPart }];
    } else if (Array.isArray(lenientPart)) {
      return lenientPart.map((p) => (typeof p === 'string' ? { text: p } : p));
    } else {
      return [lenientPart];
    }
  }

  constructor(message: MessageData) {
    this.role = message.role;
    this.content = message.content;
    this.metadata = message.metadata;
  }

  /**
   * If a message contains a `data` part, it is returned. Otherwise, the `output()`
   * method extracts the first valid JSON object or array from the text contained in
   * the message and returns it.
   *
   * @returns The structured output contained in the message.
   */
  get output(): T {
    return this.data || extractJson<T>(this.text);
  }

  toolResponseParts(): ToolResponsePart[] {
    const res = this.content.filter((part) => !!part.toolResponse);
    return res as ToolResponsePart[];
  }

  /**
   * Concatenates all `text` parts present in the message with no delimiter.
   * @returns A string of all concatenated text parts.
   */
  get text(): string {
    return this.content.map((part) => part.text || '').join('');
  }

  /**
   * Returns the first media part detected in the message. Useful for extracting
   * (for example) an image from a generation expected to create one.
   * @returns The first detected `media` part in the message.
   */
  get media(): { url: string; contentType?: string } | null {
    return this.content.find((part) => part.media)?.media || null;
  }

  /**
   * Returns the first detected `data` part of a message.
   * @returns The first `data` part detected in the message (if any).
   */
  get data(): T | null {
    return this.content.find((part) => part.data)?.data as T | null;
  }

  /**
   * Returns all tool request found in this message.
   * @returns Array of all tool request found in this message.
   */
  get toolRequests(): ToolRequestPart[] {
    return this.content.filter(
      (part) => !!part.toolRequest
    ) as ToolRequestPart[];
  }

  /**
   * Converts the Message to a plain JS object.
   * @returns Plain JS object representing the data contained in the message.
   */
  toJSON(): MessageData {
    let out: MessageData = {
      role: this.role,
      content: [...this.content],
    };
    if (this.metadata) out.metadata = this.metadata;
    return out;
  }
}

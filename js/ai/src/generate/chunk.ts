import { GenkitError } from '@genkit-ai/core';
import { extractJson } from '../extract';
import { GenerateResponseChunkData, ToolRequestPart } from '../model';

export class GenerateResponseChunk<T = unknown>
  implements GenerateResponseChunkData
{
  /** The index of the candidate this chunk corresponds to. */
  index?: number;
  /** The content generated in this chunk. */
  content: Part[];
  /** Custom model-specific data for this chunk. */
  custom?: unknown;
  /** Accumulated chunks for partial output extraction. */
  accumulatedChunks?: GenerateResponseChunkData[];

  constructor(
    data: GenerateResponseChunkData,
    accumulatedChunks?: GenerateResponseChunkData[]
  ) {
    this.index = data.index;
    this.content = data.content || [];
    this.custom = data.custom;
    this.accumulatedChunks = accumulatedChunks;
  }

  /**
   * Concatenates all `text` parts present in the chunk with no delimiter.
   * @returns A string of all concatenated text parts.
   */
  get text(): string {
    return this.content.map((part) => part.text || '').join('');
  }

  /**
   * Concatenates all `text` parts of all chunks from the response thus far.
   * @returns A string of all concatenated chunk text content.
   */
  get accumulatedText(): string {
    if (!this.accumulatedChunks)
      throw new GenkitError({
        status: 'FAILED_PRECONDITION',
        message: 'Cannot compose accumulated text without accumulated chunks.',
      });

    return this.accumulatedChunks
      ?.map((c) => c.content.map((p) => p.text || '').join(''))
      .join('');
  }

  /**
   * Returns the first media part detected in the chunk. Useful for extracting
   * (for example) an image from a generation expected to create one.
   * @returns The first detected `media` part in the chunk.
   */
  get media(): { url: string; contentType?: string } | null {
    return this.content.find((part) => part.media)?.media || null;
  }

  /**
   * Returns the first detected `data` part of a chunk.
   * @returns The first `data` part detected in the chunk (if any).
   */
  get data(): T | null {
    return this.content.find((part) => part.data)?.data as T | null;
  }

  /**
   * Returns all tool request found in this chunk.
   * @returns Array of all tool request found in this chunk.
   */
  get toolRequests(): ToolRequestPart[] {
    return this.content.filter(
      (part) => !!part.toolRequest
    ) as ToolRequestPart[];
  }

  /**
   * Attempts to extract the longest valid JSON substring from the accumulated chunks.
   * @returns The longest valid JSON substring found in the accumulated chunks.
   */
  get output(): T | null {
    if (!this.accumulatedChunks) return null;
    const accumulatedText = this.accumulatedChunks
      .map((chunk) => chunk.content.map((part) => part.text || '').join(''))
      .join('');
    return extractJson<T>(accumulatedText, false);
  }

  toJSON(): GenerateResponseChunkData {
    return { index: this.index, content: this.content, custom: this.custom };
  }
}

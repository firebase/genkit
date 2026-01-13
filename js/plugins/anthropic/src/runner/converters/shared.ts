/**
 * Copyright 2025 Google LLC
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
 * Shared utilities for converting Anthropic content blocks to Genkit Parts.
 * Uses structural typing so both stable and beta API types work with these functions.
 */

import type { Part } from 'genkit';
import type { AnthropicCitation } from '../../types.js';

/** Structural type for Anthropic citations (works with both stable and beta APIs). */
interface AnthropicCitationInput {
  type: string;
  cited_text: string;
  // document_index is optional since web search citations don't have it
  document_index?: number;
  document_title?: string | null;
  file_id?: string | null;
  start_char_index?: number;
  end_char_index?: number;
  start_page_number?: number;
  end_page_number?: number;
  start_block_index?: number;
  end_block_index?: number;
}

/**
 * Converts Anthropic's citation format (snake_case) to genkit format (camelCase).
 * Only handles document-based citations (char_location, page_location, content_block_location).
 * Skips web search and other citation types that don't reference documents.
 */
export function fromAnthropicCitation(
  citation: AnthropicCitationInput
): AnthropicCitation | undefined {
  // Skip citations without document_index (e.g., web search results)
  if (citation.document_index === undefined) {
    return undefined;
  }

  switch (citation.type) {
    case 'char_location':
      return {
        type: 'char_location',
        citedText: citation.cited_text,
        documentIndex: citation.document_index,
        documentTitle: citation.document_title ?? undefined,
        fileId: citation.file_id ?? undefined,
        startCharIndex: citation.start_char_index!,
        endCharIndex: citation.end_char_index!,
      };
    case 'page_location':
      return {
        type: 'page_location',
        citedText: citation.cited_text,
        documentIndex: citation.document_index,
        documentTitle: citation.document_title ?? undefined,
        fileId: citation.file_id ?? undefined,
        startPageNumber: citation.start_page_number!,
        endPageNumber: citation.end_page_number!,
      };
    case 'content_block_location':
      return {
        type: 'content_block_location',
        citedText: citation.cited_text,
        documentIndex: citation.document_index,
        documentTitle: citation.document_title ?? undefined,
        fileId: citation.file_id ?? undefined,
        startBlockIndex: citation.start_block_index!,
        endBlockIndex: citation.end_block_index!,
      };
    default:
      // Skip web search and other citation types - they're not from documents
      return undefined;
  }
}

/**
 * Converts a text block to a Genkit Part, including citations if present.
 * Uses structural typing for compatibility with both stable and beta APIs.
 */
export function textBlockToPart(block: {
  text: string;
  citations?: AnthropicCitationInput[] | null;
}): Part {
  if (block.citations && block.citations.length > 0) {
    const citations = block.citations
      .map((c) => fromAnthropicCitation(c))
      .filter((c): c is AnthropicCitation => c !== undefined);
    if (citations.length > 0) {
      return {
        text: block.text,
        metadata: { citations },
      };
    }
  }
  return { text: block.text };
}

/**
 * Converts a tool_use block to a Genkit Part.
 */
export function toolUseBlockToPart(block: {
  id: string;
  name: string;
  input: unknown;
}): Part {
  return {
    toolRequest: {
      ref: block.id,
      name: block.name,
      input: block.input,
    },
  };
}

/**
 * Converts a thinking block to a Genkit Part, including signature metadata if present.
 */
export function thinkingBlockToPart(block: {
  thinking: string;
  signature?: string;
}): Part {
  if (block.signature !== undefined) {
    return {
      reasoning: block.thinking,
      metadata: { thoughtSignature: block.signature },
    };
  }
  return { reasoning: block.thinking };
}

/**
 * Converts a redacted thinking block to a Genkit Part.
 */
export function redactedThinkingBlockToPart(block: { data: string }): Part {
  return { custom: { redactedThinking: block.data } };
}

/**
 * Converts a web_search_tool_result block to a Genkit Part.
 */
export function webSearchToolResultBlockToPart(block: {
  tool_use_id: string;
  content: unknown;
}): Part {
  return {
    text: `[Anthropic server tool result ${block.tool_use_id}] ${JSON.stringify(block.content)}`,
    metadata: {
      anthropicServerToolResult: {
        type: 'web_search_tool_result',
        toolUseId: block.tool_use_id,
        content: block.content,
      },
    },
  };
}

// --- Delta converters for streaming ---

/**
 * Converts a text_delta to a Genkit Part.
 */
export function textDeltaToPart(delta: { text: string }): Part {
  return { text: delta.text };
}

/**
 * Converts a thinking_delta to a Genkit Part.
 */
export function thinkingDeltaToPart(delta: { thinking: string }): Part {
  return { reasoning: delta.thinking };
}

/**
 * Converts a citations_delta to a Genkit Part for streaming.
 * Returns a text part with empty text and citation data in metadata.
 * Empty text is intentional: genkit's `.text` getter concatenates all text parts,
 * so empty strings contribute nothing to the final text while preserving the citation
 * in the parts array for consumers who need to access citation metadata.
 */
export function citationsDeltaToPart(delta: {
  citation: AnthropicCitationInput;
}): Part | undefined {
  const citation = fromAnthropicCitation(delta.citation);
  if (citation) {
    return {
      text: '',
      metadata: { citations: [citation] },
    };
  }
  return undefined;
}

/**
 * Error for unsupported input_json_delta in streaming.
 */
export function inputJsonDeltaError(): Error {
  return new Error(
    'Anthropic streaming tool input (input_json_delta) is not yet supported. Please disable streaming or upgrade this plugin.'
  );
}

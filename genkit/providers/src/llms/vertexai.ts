import {
  Content,
  FunctionDeclaration,
  FunctionDeclarationSchemaType,
  GenerateContentRequest,
  GenerativeModel,
  HarmBlockThreshold,
  HarmCategory,
  Part,
  VertexAI,
} from '@google-cloud/vertexai';
import { CommonLlmOptions, ToolCall, ToolSchema } from '@google-genkit/ai';
import { chatModelFactory, Message, Role } from '@google-genkit/ai/chat';
import { textModelFactory } from '@google-genkit/ai/text';
import { getProjectId } from '@google-genkit/common';
import logging from '@google-genkit/common/logging';
import { z } from 'zod';

const HarmCategorySchema = z.nativeEnum(HarmCategory);
const HarmBlockThresholdSchema = z.nativeEnum(HarmBlockThreshold);

const SafetySettingSchema = z.object({
  category: HarmCategorySchema,
  threshold: HarmBlockThresholdSchema,
});

// Mapping Role to Vertex AI roles
function mapToVertexRoles(role: Role): string {
  // TODO: system message not supported yet
  // TODO: Figure out how to represent tool calls
  switch (role) {
    case Role.User:
      return 'user';
    case Role.Model:
      return 'model';
    case Role.Tool:
      return 'function';
    default:
      return 'unknown';
  }
}

const toVertexAiTool = (
  tool: z.infer<typeof ToolSchema>
): FunctionDeclaration => {
  return {
    name: tool.name,
    description: tool.description,
    parameters: convertSchemaProperty(tool.schema.input),
  };
};

// Translate JSON schema to Vertex AI's format. Specifically, the type field needs be mapped.
// Since JSON schemas can include nested arrays/objects, we have to recursively map the type field
// in all nested fields.
const convertSchemaProperty = (property) => {
  if (property.type === 'object') {
    const nestedProperties = {};
    Object.keys(property.properties).forEach((key) => {
      nestedProperties[key] = convertSchemaProperty(property.properties[key]);
    });
    return {
      type: FunctionDeclarationSchemaType.OBJECT,
      properties: nestedProperties,
      required: property.required,
    };
  } else if (property.type === 'array') {
    return {
      type: FunctionDeclarationSchemaType.ARRAY,
      items: convertSchemaProperty(property.items),
    };
  } else {
    return {
      type: FunctionDeclarationSchemaType[property.type.toUpperCase()],
    };
  }
};

const setModelOptions = (
  model: GenerativeModel,
  options: z.infer<typeof VertexAiModelOptions>
) => {
  if (options) {
    if (!model.generation_config) {
      model.generation_config = {};
    }

    if (!model.safety_settings) {
      model.safety_settings = [];
    }

    if (options.stopSequences) {
      model.generation_config.stop_sequences = options.stopSequences;
    }

    if (options.maxOutputTokens) {
      model.generation_config.max_output_tokens = options.maxOutputTokens;
    }

    if (options.candidateCount) {
      model.generation_config.candidate_count = options.candidateCount;
    }

    if (options.safetySettings) {
      options.safetySettings.forEach((setting) =>
        model.safety_settings?.push(setting)
      );
    }

    if (options.hasOwnProperty('temperature')) {
      model.generation_config.temperature = options.temperature;
    }
    if (options.hasOwnProperty('topK')) {
      model.generation_config.top_k = options.topK;
    }
    if (options.hasOwnProperty('topP')) {
      model.generation_config.top_p = options.topP;
    }
  }
};

/**
 * Configures a Vertex AI chat model.
 * @deprecated
 */
export function configureVertexAiChatModel(params: {
  projectId?: string;
  location?: string;
  modelName: string;
}) {
  return chatModelFactory(
    'google-vertex',
    params.modelName,
    VertexAiModelOptions,
    async (input, options) => {
      const vertexClient = new VertexAI({
        project: params.projectId || getProjectId(),
        location: params.location || 'us-central1',
      });

      const model = vertexClient.preview.getGenerativeModel({
        model: params.modelName,
      });
      if (options) {
        setModelOptions(model, options);
      }

      // Mapping GenKit message format to Vertex AI message
      const history = input.messages.slice(0, -1).map(
        (message: Message): Content => ({
          role: mapToVertexRoles(message.role),
          parts: [{ text: message.message }],
        })
      );

      const message = input.messages[input.messages.length - 1];
      const tools = [
        {
          function_declarations: input.tools
            ? input.tools.map((tool) => toVertexAiTool(tool))
            : [],
        },
      ];
      const chat = model.startChat({
        history: history.length ? history : undefined,
        tools: tools.length ? tools : undefined,
      });
      const res = await chat.sendMessage(message.message);

      // TODO: Confirm that parts[0] is correct, as opposed to mapping parts
      const responseText = res.response.candidates[0].content.parts[0].text;
      const functionCall =
        res.response.candidates[0].content.parts[0].functionCall;
      logging.debug(`Vertex AI Response: ${JSON.stringify(res)}`);

      const toolCalls: ToolCall[] = [];
      if (functionCall) {
        toolCalls.push({
          toolName: functionCall.name,
          arguments: functionCall.args,
        });
      }
      return {
        completion: responseText || '',
        toolCalls,
        stats: {}, // TODO: fill these out.
      };
    }
  );
}

const VertexAiModelOptions = CommonLlmOptions.extend({
  safetySettings: z.array(SafetySettingSchema).optional(),
  candidateCount: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  stopSequences: z.array(z.string()).optional(),
});

/**
 * Configures a Vertex AI chat model.
 */
export function configureVertexAiTextModel(params: {
  projectId?: string;
  location?: string;
  modelName: string;
}) {
  return textModelFactory(
    'google-vertex',
    params.modelName,
    VertexAiModelOptions,
    async (input, options, streamingCallback) => {
      const request = {
        contents: [],
        tools: input.tools
          ? input.tools.map((tool) => toVertexAiTool(tool))
          : undefined,
      } as GenerateContentRequest;
      if (typeof input.prompt.prompt === 'string') {
        request.contents.push({
          role: 'user',
          parts: [{ text: input.prompt.prompt }],
        });
      } else {
        const parts = [] as Part[];
        input.prompt.prompt.forEach((part) => {
          if (typeof part === 'string') {
            parts.push({
              text: part,
            });
          } else {
            parts.push({
              inline_data: {
                data: part.uri,
                mime_type: part.mimeType,
              },
            });
          }
        });
        request.contents.push({ role: 'user', parts });
      }

      logging.debug(request, 'vertex request');

      const vertexAI = new VertexAI({
        project: params.projectId || getProjectId(),
        location: params.location || 'us-central1',
      });

      // Instantiate the model
      const model = vertexAI.preview.getGenerativeModel({
        model: params.modelName,
      });
      if (options) {
        setModelOptions(model, options);
      }

      // Create the response stream
      const responseStream = await model.generateContentStream(request);
      for await (const item of responseStream.stream) {
        const chunkText = item?.candidates[0]?.content?.parts[0]?.text;
        if (chunkText) {
          streamingCallback?.onChunk(chunkText);
        }
      }

      // Wait for the response stream to complete
      const aggregatedResponse = await responseStream.response;

      logging.debug(
        JSON.stringify(responseStream, undefined, '  '),
        'vertext response'
      );

      // Select the text from the response
      const fullTextResponse =
        aggregatedResponse?.candidates[0]?.content?.parts[0]?.text;

      if (!fullTextResponse) {
        throw new Error('unable to parse response');
      }

      return {
        completion: fullTextResponse,
        stats: {}, // TODO: fill these out.
      };
    }
  );
}

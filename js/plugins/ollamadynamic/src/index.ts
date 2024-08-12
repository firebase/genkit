import {
  CandidateData,
  defineModel,
  GenerateRequest,
  GenerateResponseData,
  GenerationCommonConfigSchema,
  getBasicUsageStats,
  MessageData,
} from '@genkit-ai/ai/model';
import { genkitPlugin, Plugin } from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';


type ApiType = 'chat' | 'generate';

// type RequestHeaders =
//   | Record<string, string>
//   | ((
//       params: { serverAddress: string; model: ModelDefinitionDynamic },
//       request: GenerateRequest
//     ) => Promise<Record<string, string> | void>);

// type ServerDynamic =
//     | string
//     | (( request: GenerateRequest
//       ) => Promise<string>);

// type ModelDefinitionDynamic = | { name: string; type?: ApiType }
//                        | (( request: GenerateRequest
//                        ) => Promise<{ name: string; type?: ApiType }>);

type DynamicConfiguration = 
                      (
                        ( 
                        params: { modelName:string, requestId: string },
                        request: GenerateRequest
                        ) => Promise<{ serverAddress: string; name: string; type?: ApiType; authToken:Record<string, string>}>
                      );                  

// export interface OllamaDynamicPluginParams {
//   serverAddress: ServerDynamic;
//   model: ModelDefinitionDynamic;
//   requestHeaders?: RequestHeaders;
// }

export interface OllamaDynamicPluginParams {
  dynamicConfig: DynamicConfiguration;
}

export const ollamadynamic: Plugin<[OllamaDynamicPluginParams]> = genkitPlugin(
  'ollamadynamic',
  async (params: OllamaDynamicPluginParams) => {
    return {
      models: [
        //ollamadynamicModel(params.model, params.serverAddress, params.requestHeaders)
        ollamadynamicModel(params.dynamicConfig)
      ],
    };
  }
);



// function ollamadynamicModel(
//   modelDynamic: ModelDefinitionDynamic,
//   serverAddressDynamic: ServerDynamic,
//   requestHeaders?: RequestHeaders
// ) {
  function ollamadynamicModel(
    dynamicConfig: DynamicConfiguration
  ) {
  return defineModel(
    {
      name: `ollamadynamic/model`,
      label: `Ollama Dynamic`,
      configSchema: GenerationCommonConfigSchema,
      supports: {
        multiturn: true,
        media: true,
        tools: true,
        systemRole: true,
      },
    },
    async (input, streamingCallback) => {

      const options: Record<string, any> = {};


      let requestId:string = "";
      let modelName:string = "";
      if (input.context?.[0]?.metadata) {
        requestId = input.context?.[0]?.metadata["requestId"];
        modelName = input.context?.[0]?.metadata["modelName"];
      }

      logger.debug(`ollama dynamic context (${JSON.stringify( input.context?.[0])})`);

      let config: any;
      // config = typeof dynamicConfig === 'function' ? 
      // await dynamicConfig({modelName,requestId},input) : 
      // dynamicConfig;

      config = await dynamicConfig({modelName,requestId},input) as { serverAddress: string; name: string; type?: ApiType; authToken:Record<string, string>};






      let model = {name:config.name, type:config.type};
      let requestHeaders = config.authToken;
      let serverAddress = config.serverAddress;


      
      if (input.config?.hasOwnProperty('temperature')) {
        options.temperature = input.config?.temperature;
      }
      if (input.config?.hasOwnProperty('topP')) {
        options.top_p = input.config?.topP;
      }
      if (input.config?.hasOwnProperty('topK')) {
        options.top_k = input.config?.topK;
      }
      if (input.config?.hasOwnProperty('stopSequences')) {
        options.stop = input.config?.stopSequences?.join('');
      }
      if (input.config?.hasOwnProperty('maxOutputTokens')) {
        options.num_predict = input.config?.maxOutputTokens;
      }
      const type = model.type ?? 'chat';
      const request = toOllamadynamicRequest(
        model.name,
        input,
        options,
        type,
        !!streamingCallback
      );
      logger.debug(request, `ollama dynamic request (${type})`);

      const extraHeaders = requestHeaders
        ? requestHeaders
        : {};

      let res;
      try {
        res = await fetch(
          serverAddress + (type === 'chat' ? '/api/chat' : '/api/generate'),
          {
            method: 'POST',
            body: JSON.stringify(request),
            headers: {
              'Content-Type': 'application/json',
              ...extraHeaders,
            },
          }
        );
      } catch (e) {
        const cause = (e as any).cause;
        if (cause) {
          if (
            cause instanceof Error &&
            cause.message?.includes('ECONNREFUSED')
          ) {
            cause.message += '. Make sure ollama server is running.';
          }
          throw cause;
        }
        throw e;
      }
      if (!res.body) {
        throw new Error('Response has no body');
      }

      const responseCandidates: CandidateData[] = [];

      if (streamingCallback) {
        const reader = res.body.getReader();
        const textDecoder = new TextDecoder();
        let textResponse = '';
        for await (const chunk of readChunks(reader)) {
          const chunkText = textDecoder.decode(chunk);
          const json = JSON.parse(chunkText);
          const message = parseMessage(json, type);
          streamingCallback({
            index: 0,
            content: message.content,
          });
          textResponse += message.content[0].text;
        }
        responseCandidates.push({
          index: 0,
          finishReason: 'stop',
          message: {
            role: 'model',
            content: [
              {
                text: textResponse,
              },
            ],
          },
        } as CandidateData);
      } else {
        const txtBody = await res.text();
        const json = JSON.parse(txtBody);
        logger.debug(txtBody, 'ollama raw response');

        responseCandidates.push({
          index: 0,
          finishReason: 'stop',
          message: parseMessage(json, type),
        } as CandidateData);
      }

      return {
        candidates: responseCandidates,
        usage: getBasicUsageStats(input.messages, responseCandidates),
      } as GenerateResponseData;
    }
  );
}


function parseMessage(response: any, type: ApiType): MessageData {
  if (response.error) {
    throw new Error(response.error);
  }
  if (type === 'chat') {
    return {
      role: toGenkitRole(response.message.role),
      content: [
        {
          text: response.message.content,
        },
      ],
    };
  } else {
    return {
      role: 'model',
      content: [
        {
          text: response.response,
        },
      ],
    };
  }
}

function toOllamadynamicRequest(
  name: string,
  input: GenerateRequest,
  options: Record<string, any>,
  type: ApiType,
  stream: boolean
) {
  const request = {
    model: name,
    options,
    stream,
  } as any;
  if (type === 'chat') {
    const messages: Message[] = [];
    input.messages.forEach((m) => {
      let messageText = '';
      const images: string[] = [];
      m.content.forEach((c) => {
        if (c.text) {
          messageText += c.text;
        }
        if (c.media) {
          images.push(c.media.url);
        }
      });
      messages.push({
        role: toOllamaRole(m.role),
        content: messageText,
        images: images.length > 0 ? images : undefined,
      });
    });
    request.messages = messages;
  } else {
    request.prompt = getPrompt(input);
    request.system = getSystemMessage(input);
  }
  return request;
}

function toOllamaRole(role) {
  if (role === 'model') {
    return 'assistant';
  }
  return role; // everything else seems to match
}

function toGenkitRole(role) {
  if (role === 'assistant') {
    return 'model';
  }
  return role; // everything else seems to match
}

function readChunks(reader) {
  return {
    async *[Symbol.asyncIterator]() {
      let readResult = await reader.read();
      while (!readResult.done) {
        yield readResult.value;
        readResult = await reader.read();
      }
    },
  };
}

function getPrompt(input: GenerateRequest): string {
  return input.messages
    .filter((m) => m.role !== 'system')
    .map((m) => m.content.map((c) => c.text).join())
    .join();
}

function getSystemMessage(input: GenerateRequest): string {
  return input.messages
    .filter((m) => m.role === 'system')
    .map((m) => m.content.map((c) => c.text).join())
    .join();
}

interface Message {
  role: string;
  content: string;
  images?: string[];
}

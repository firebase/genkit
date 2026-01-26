/**
 * Copyright 2024 Xavier Portilla Edo
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
/* eslint-disable  @typescript-eslint/no-explicit-any */

import {
  GenerateRequest,
  GenerationCommonConfigSchema,
  Message,
  MessageData,
  ModelReference,
  Part,
  Role,
  ToolRequestPart,
} from 'genkit';

import {
  GenerateResponseChunkData,
  ModelAction,
  ModelResponseData,
  ToolDefinition,
  modelRef,
} from 'genkit/model';

import { model } from 'genkit/plugin';

import {
  Message as AwsMessge,
  BedrockRuntimeClient,
  ContentBlock,
  ContentBlockDelta,
  ConverseCommand,
  ConverseCommandInput,
  ConverseCommandOutput,
  ConverseStreamCommand,
  ConverseStreamCommandInput,
  ConverseStreamCommandOutput,
  ImageFormat,
  SystemContentBlock,
  Tool,
  ToolUseBlock,
} from '@aws-sdk/client-bedrock-runtime';

export const amazonNovaProV1 = modelRef({
  name: 'aws-bedrock/amazon.nova-pro-v1:0',
  info: {
    versions: ['amazon.nova-pro-v1:0'],
    label: 'Amazon - Nova Pro V1',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const amazonNovaLiteV1 = modelRef({
  name: 'aws-bedrock/amazon.nova-lite-v1:0',
  info: {
    versions: ['amazon.nova-lite-v1:0'],
    label: 'Amazon - Nova Lite V1',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const amazonNovaMicroV1 = modelRef({
  name: 'aws-bedrock/amazon.nova-micro-v1:0',
  info: {
    versions: ['amazon.nova-micro-v1:0'],
    label: 'Amazon - Nova Micro V1',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const amazonTitanTextG1PremierV1 = modelRef({
  name: 'aws-bedrock/amazon.titan-text-premier-v1:0',
  info: {
    versions: ['amazon.titan-text-premier-v1:0'],
    label: 'Amazon - Titan Text Premier G1 V1',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const amazonTitanTextG1ExpressV1 = modelRef({
  name: 'aws-bedrock/amazon.titan-text-express-v1',
  info: {
    versions: ['amazon.titan-text-express-v1'],
    label: 'Amazon - Titan Text Express G1 V1',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const amazonTitanTextG1LiteV1 = modelRef({
  name: 'aws-bedrock/amazon.titan-text-lite-v1',
  info: {
    versions: ['amazon.titan-text-lite-v1'],
    label: 'Amazon - Titan Text Lite G1 V1',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const cohereCommandRV1 = modelRef({
  name: 'aws-bedrock/cohere.command-r-v1:0',
  info: {
    versions: ['cohere.command-r-v1:0'],
    label: 'Cohere - Command R',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const cohereCommandRPlusV1 = modelRef({
  name: 'aws-bedrock/cohere.command-r-plus-v1:0',
  info: {
    versions: ['cohere.command-r-plus-v1:0'],
    label: 'Cohere - Command R+',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const cohereCommandLightV14 = modelRef({
  name: 'aws-bedrock/cohere.command-light-text-v14',
  info: {
    versions: ['cohere.command-light-text-v14'],
    label: 'Cohere - Command Light V14',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const cohereCommandV14 = modelRef({
  name: 'aws-bedrock/cohere.command-text-v14',
  info: {
    versions: ['cohere.command-text-v14'],
    label: 'Cohere - Command V14',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const anthropicClaude35HaikuV1 = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.anthropic.claude-3-5-haiku-20241022-v1:0`,
    info: {
      versions: [`${inferenceRegion}.anthropic.claude-3-5-haiku-20241022-v1:0`],
      label: 'Anthropic - Claude 3.5 Haiku V1',
      supports: {
        multiturn: true,
        tools: true,
        media: false,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const anthropicClaude3HaikuV1 = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.anthropic.claude-3-haiku-20240307-v1:0`,
    info: {
      versions: [`${inferenceRegion}.anthropic.claude-3-haiku-20240307-v1:0`],
      label: 'Anthropic - Claude 3 Haiku V1',
      supports: {
        multiturn: true,
        tools: true,
        media: false,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const anthropicClaude3OpusV1 = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.anthropic.claude-3-opus-20240229-v1:0`,
    info: {
      versions: [`${inferenceRegion}.anthropic.claude-3-opus-20240229-v1:0`],
      label: 'Anthropic - Claude 3 Opus V1',
      supports: {
        multiturn: true,
        tools: true,
        media: false,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const anthropicClaude37SonnetV1 = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.anthropic.claude-3-7-sonnet-20250219-v1:0`,
    info: {
      versions: [
        `${inferenceRegion}.anthropic.claude-3-7-sonnet-20250219-v1:0`,
      ],
      label: 'Anthropic - Claude 3.7 Sonnet V1',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const anthropicClaude35SonnetV2 = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.anthropic.claude-3-5-sonnet-20241022-v2:0`,
    info: {
      versions: [
        `${inferenceRegion}.anthropic.claude-3-5-sonnet-20241022-v2:0`,
      ],
      label: 'Anthropic - Claude 3.5 Sonnet V2',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const anthropicClaude35SonnetV1 = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.anthropic.claude-3-5-sonnet-20240620-v1:0`,
    info: {
      versions: [
        `${inferenceRegion}.anthropic.claude-3-5-sonnet-20240620-v1:0`,
      ],
      label: 'Anthropic - Claude 3.5 Sonnet V1',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const anthropicClaude3SonnetV1 = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.anthropic.claude-3-sonnet-20240229-v1:0`,
    info: {
      versions: [`${inferenceRegion}.anthropic.claude-3-sonnet-20240229-v1:0`],
      label: 'Anthropic - Claude 3 Sonnet V1',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const anthropicClaude21V1 = modelRef({
  name: 'aws-bedrock/anthropic.claude-v2:1',
  info: {
    versions: ['anthropic.claude-v2:1'],
    label: 'Anthropic - Claude 2.1 V1',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const anthropicClaude2V1 = modelRef({
  name: 'aws-bedrock/anthropic.claude-v2',
  info: {
    versions: ['anthropic.claude-v2'],
    label: 'Anthropic - Claude 2 V1',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const anthropicClaudeInstantV1 = modelRef({
  name: 'aws-bedrock/anthropic.claude-instant-v1',
  info: {
    versions: ['anthropic.claude-instant-v1'],
    label: 'Anthropic - Claude Instant V1',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const mistralLarge2402V1 = modelRef({
  name: 'aws-bedrock/mistral.mistral-large-2402-v1:0',
  info: {
    versions: ['mistral.mistral-large-2402-v1:0'],
    label: 'Mistral - Large (24.02)',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const mistralSmall2402V1 = modelRef({
  name: 'aws-bedrock/mistral.mistral-small-2402-v1:0',
  info: {
    versions: ['mistral.mistral-small-2402-v1:0'],
    label: 'Mistral - Small (24.02)',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const mistral7BInstructV02 = modelRef({
  name: 'aws-bedrock/mistral.mistral-7b-instruct-v0:2',
  info: {
    versions: ['mistral.mistral-7b-instruct-v0:2'],
    label: 'Mistral - 7B Instruct',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const mistral8x7BInstructV01 = modelRef({
  name: 'aws-bedrock/mistral.mixtral-8x7b-instruct-v0:1',
  info: {
    versions: ['mistral.mixtral-8x7b-instruct-v0:1'],
    label: 'Mistral - 8x7B Instruct',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const ai21Jamba15LargeV1 = modelRef({
  name: 'aws-bedrock/ai21.jamba-1-5-large-v1:0',
  info: {
    versions: ['ai21.jamba-1-5-large-v1:0'],
    label: 'AI21 - Jambda 1.5 Large',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const ai21Jamba15MiniV1 = modelRef({
  name: 'aws-bedrock/ai21.jamba-1-5-mini-v1:0',
  info: {
    versions: ['ai21.jamba-1-5-mini-v1:0'],
    label: 'AI21 - Jambda 1.5 Mini',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const ai21JambaInstructV1 = modelRef({
  name: 'aws-bedrock/ai21.jamba-instruct-v1:0',
  info: {
    versions: ['ai21.jamba-instruct-v1:0'],
    label: 'AI21 - Jambda Instruct',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const ai21Jurassic2MidV1 = modelRef({
  name: 'aws-bedrock/ai21.j2-mid-v1',
  info: {
    versions: ['ai21.j2-mid-v1'],
    label: 'AI21 - Jurassic-2 Mid',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const ai21Jurassic2UltraV1 = modelRef({
  name: 'aws-bedrock/ai21.j2-ultra-v1',
  info: {
    versions: ['ai21.j2-ultra-v1'],
    label: 'AI21 - Jurassic-2 Ultra',
    supports: {
      multiturn: true,
      tools: false,
      media: false,
      systemRole: false,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const metaLlama3370BInstruct = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.meta.llama3-3-70b-instruct-v1:0`,
    info: {
      versions: [`${inferenceRegion}.meta.llama3-3-70b-instruct-v1:0`],
      label: 'Meta - Llama 3.3 70b Instruct',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const metaLlama3211BInstruct = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.meta.llama3-2-11b-instruct-v1:0`,
    info: {
      versions: [`${inferenceRegion}.meta.llama3-2-11b-instruct-v1:0`],
      label: 'Meta - Llama 3.2 11b Instruct',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const metaLlama321BInstruct = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.meta.llama3-2-1b-instruct-v1:0`,
    info: {
      versions: [`${inferenceRegion}.meta.llama3-2-1b-instruct-v1:0`],
      label: 'Meta - Llama 3.2 1b Instruct',
      supports: {
        multiturn: true,
        tools: false,
        media: false,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const metaLlama323BInstruct = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.meta.llama3-2-3b-instruct-v1:0`,
    info: {
      versions: [`${inferenceRegion}.meta.llama3-2-3b-instruct-v1:0`],
      label: 'Meta - Llama 3.2 3b Instruct',
      supports: {
        multiturn: true,
        tools: false,
        media: false,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const metaLlama3290BInstruct = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.meta.llama3-2-90b-instruct-v1:0`,
    info: {
      versions: [`${inferenceRegion}.meta.llama3-2-90b-instruct-v1:0`],
      label: 'Meta - Llama 3.2 90b Instruct',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const metaLlama3170BInstruct = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.meta.llama3-1-70b-instruct-v1:0`,
    info: {
      versions: [`${inferenceRegion}.meta.llama3-1-70b-instruct-v1:0`],
      label: 'Meta - Llama 3.1 70b Instruct',
      supports: {
        multiturn: true,
        tools: false,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const metaLlama318BInstruct = (
  inferenceRegion: string = 'us'
): ModelReference<typeof GenerationCommonConfigSchema> => {
  return modelRef({
    name: `aws-bedrock/${inferenceRegion}.meta.llama3-1-8b-instruct-v1:0`,
    info: {
      versions: [`${inferenceRegion}.meta.llama3-1-8b-instruct-v1:0`],
      label: 'Meta - Llama 3.1 8b Instruct',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text', 'json'],
      },
    },
    configSchema: GenerationCommonConfigSchema,
  });
};

export const metaLlama370BInstruct = modelRef({
  name: 'aws-bedrock/meta.llama3-70b-instruct-v1:0',
  info: {
    versions: ['meta.llama3-70b-instruct-v1:0'],
    label: 'Meta - Llama 3 70b Instruct',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const metaLlama38BInstruct = modelRef({
  name: 'aws-bedrock/meta.llama3-8b-instruct-v1:0',
  info: {
    versions: ['meta.llama3-8b-instruct-v1:0'],
    label: 'Meta - Llama 3 8b Instruct',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text', 'json'],
    },
  },
  configSchema: GenerationCommonConfigSchema,
});

export const SUPPORTED_AWS_BEDROCK_MODELS = (
  inferenceRegion: string = 'us'
): Record<string, any> => {
  return {
    'amazon.nova-pro-v1:0': amazonNovaProV1,
    'amazon.nova-lite-v1:0': amazonNovaLiteV1,
    'amazon.nova-micro-v1:0': amazonNovaMicroV1,
    'amazon.titan-text-premier-v1:0': amazonTitanTextG1PremierV1,
    'amazon.titan-text-express-v1': amazonTitanTextG1ExpressV1,
    'amazon.titan-text-lite-v1': amazonTitanTextG1LiteV1,
    'cohere.command-r-v1:0': cohereCommandRV1,
    'cohere.command-r-plus-v1:0': cohereCommandRPlusV1,
    'cohere.command-light-text-v14': cohereCommandLightV14,
    'cohere.command-text-v14': cohereCommandV14,
    'mistral.mistral-large-2402-v1:0': mistralLarge2402V1,
    'mistral.mistral-small-2402-v1:0': mistralSmall2402V1,
    'mistral.mistral-7b-instruct-v0:2': mistral7BInstructV02,
    'mistral.mixtral-8x7b-instruct-v0:1': mistral8x7BInstructV01,
    'ai21.jamba-1-5-large-v1:0': ai21Jamba15LargeV1,
    'ai21.jamba-1-5-mini-v1:0': ai21Jamba15MiniV1,
    'ai21.jamba-instruct-v1:0': ai21JambaInstructV1,
    'ai21.j2-mid-v1': ai21Jurassic2MidV1,
    'ai21.j2-ultra-v1': ai21Jurassic2UltraV1,
    [`${inferenceRegion}.meta.llama3-3-70b-instruct-v1:0`]:
      metaLlama3370BInstruct(inferenceRegion),
    [`${inferenceRegion}.meta.llama3-2-11b-instruct-v1:0`]:
      metaLlama3211BInstruct(inferenceRegion),
    [`${inferenceRegion}.meta.llama3-2-1b-instruct-v1:0`]:
      metaLlama321BInstruct(inferenceRegion),
    [`${inferenceRegion}.meta.llama3-2-3b-instruct-v1:0`]:
      metaLlama323BInstruct(inferenceRegion),
    [`${inferenceRegion}.meta.llama3-2-90b-instruct-v1:0`]:
      metaLlama3290BInstruct(inferenceRegion),
    [`${inferenceRegion}.meta.llama3-1-70b-instruct-v1:0`]:
      metaLlama3170BInstruct(inferenceRegion),
    [`${inferenceRegion}.meta.llama3-1-8b-instruct-v1:0`]:
      metaLlama318BInstruct(inferenceRegion),
    'meta.llama3-70b-instruct-v1:0': metaLlama370BInstruct,
    'meta.llama3-8b-instruct-v1:0': metaLlama38BInstruct,
    'anthropic.claude-v2:1': anthropicClaude21V1,
    'anthropic.claude-v2': anthropicClaude2V1,
    'anthropic.claude-instant-v1': anthropicClaudeInstantV1,
    [`${inferenceRegion}.anthropic.claude-3-5-haiku-20241022-v1:0`]:
      anthropicClaude35HaikuV1(inferenceRegion),
    [`${inferenceRegion}.anthropic.claude-3-7-sonnet-20250219-v1:0`]:
      anthropicClaude37SonnetV1(inferenceRegion),
    [`${inferenceRegion}.anthropic.claude-3-5-sonnet-20241022-v2:0`]:
      anthropicClaude35SonnetV2(inferenceRegion),
    [`${inferenceRegion}.anthropic.claude-3-5-sonnet-20240620-v1:0`]:
      anthropicClaude35SonnetV1(inferenceRegion),
    [`${inferenceRegion}.anthropic.claude-3-opus-20240229-v1:0`]:
      anthropicClaude3OpusV1(inferenceRegion),
    [`${inferenceRegion}.anthropic.claude-3-haiku-20240307-v1:0`]:
      anthropicClaude3HaikuV1(inferenceRegion),
    [`${inferenceRegion}.anthropic.claude-3-sonnet-20240229-v1:0`]:
      anthropicClaude3SonnetV1(inferenceRegion),
  };
};

function toAwsBedrockbRole(role: Role): string {
  switch (role) {
    case 'user':
      return 'user';
    case 'model':
      return 'assistant';
    case 'system':
      return 'system';
    case 'tool':
      return 'tool';
    default:
      throw new Error(`role ${role} doesn't map to an AWS Bedrock role.`);
  }
}

function toAwsBedrockTool(tool: ToolDefinition): Tool {
  return {
    toolSpec: {
      name: tool.name,
      description: tool.description,
      inputSchema: tool.inputSchema ? { json: tool.inputSchema } : undefined,
    },
  };
}
const regex = /data:.*base64,/;
const getDataPart = (dataUrl: string) => dataUrl.replace(regex, '');

export function toAwsBedrockTextAndMedia(
  part: Part,
  imageFormat: ImageFormat
): ContentBlock {
  if (part.text) {
    return {
      text: part.text,
    };
  } else if (part.media) {
    const imageBuffer = new Uint8Array(
      Buffer.from(getDataPart(part.media.url), 'base64')
    );

    return {
      image: {
        source: { bytes: imageBuffer },
        format: imageFormat,
      },
    };
  }
  throw Error(
    `Unsupported genkit part fields encountered for current message role: ${part}.`
  );
}

export function getSystemMessage(
  messages: MessageData[]
): SystemContentBlock[] | null {
  for (const message of messages) {
    if (message.role === 'system') {
      return [
        {
          text: message.content[0].text!,
        },
      ];
    }
  }
  return null;
}

export function toAwsBedrockMessages(
  messages: MessageData[],
  imageFormat: ImageFormat = 'png'
): AwsMessge[] {
  const awsBedrockMsgs: AwsMessge[] = [];
  for (const message of messages) {
    const msg = new Message(message);
    const role = toAwsBedrockbRole(message.role);
    switch (role) {
      case 'system': {
        break;
      }
      case 'user': {
        const textAndMedia = msg.content.map((part) =>
          toAwsBedrockTextAndMedia(part, imageFormat)
        );
        if (textAndMedia.length > 1) {
          awsBedrockMsgs.push({
            role: role,
            content: textAndMedia,
          });
        } else {
          awsBedrockMsgs.push({
            role: role,
            content: [
              {
                text: msg.text,
              },
            ],
          });
        }
        break;
      }
      case 'assistant': {
        // Request to call the tool

        const toolCalls: ToolUseBlock[] = msg.content
          .filter((part) => part.toolRequest)
          .map((part) => {
            if (!part.toolRequest) {
              throw Error(
                'Mapping genkit message to openai tool call content part but message.toolRequest not provided.'
              );
            }
            return {
              toolUseId: part.toolRequest.ref || '',
              name: part.toolRequest.name,
              input: part.toolRequest.input as any,
            };
          });
        if (toolCalls?.length > 0) {
          awsBedrockMsgs.push({
            role: role,
            content: toolCalls.map((toolCall) => ({ toolUse: toolCall })),
          });
        } else {
          awsBedrockMsgs.push({
            role: role,
            content: [
              {
                text: msg.text,
              },
            ],
          });
        }
        break;
      }
      case 'tool': {
        // result of the tool
        const toolResponseParts = msg.toolResponseParts();

        toolResponseParts.map((part) => {
          const toolresult: AwsMessge = {
            role: 'user',
            content: [
              {
                toolResult: {
                  toolUseId: part.toolResponse.ref,
                  content: [
                    {
                      json: {
                        result: part.toolResponse.output as {
                          [key: string]: any;
                        },
                      },
                    },
                  ],
                },
              },
            ],
          };
          awsBedrockMsgs.push(toolresult);
        });
        break;
      }
      default:
        throw new Error('unrecognized role');
    }
  }
  return awsBedrockMsgs;
}

const finishReasonMap: Record<
  NonNullable<string>,
  ModelResponseData['finishReason']
> = {
  max_tokens: 'length',
  end_turn: 'stop',
  stop_sequence: 'stop',
  tool_use: 'stop',
  content_filtered: 'blocked',
  guardrail_intervened: 'blocked',
};

function fromAwsBedrockToolCall(toolCall: ToolUseBlock) {
  if (!('toolUseId' in toolCall)) {
    throw Error(
      `Unexpected AWS chunk choice. tool_calls was provided but one or more tool_calls is missing.`
    );
  }
  const f = toolCall;
  return [
    {
      toolRequest: {
        name: f.name,
        ref: toolCall.toolUseId,
        input: f.input,
      },
    },
  ];
}

function extractTextFromContent(content: ContentBlock[] | undefined): string {
  if (!content) return '';

  // Find the content block that contains text (skip reasoningContent blocks)
  for (const block of content) {
    if ('text' in block && block.text) {
      return block.text;
    }
  }
  return '';
}

function fromAwsBedrockChoice(
  choice: ConverseCommandOutput,
  jsonMode = false
): ModelResponseData {
  // Find all tool use blocks in the content array
  const toolRequestParts: any[] = [];
  if (choice.output?.message?.content) {
    for (const contentBlock of choice.output.message.content) {
      if (contentBlock.toolUse) {
        toolRequestParts.push(...fromAwsBedrockToolCall(contentBlock.toolUse));
      }
    }
  }

  const textContent = extractTextFromContent(choice.output?.message?.content);

  return {
    finishReason:
      'stopReason' in choice ? finishReasonMap[choice.stopReason!] : 'other',
    message: {
      role: 'model',
      content:
        Array.isArray(toolRequestParts) && toolRequestParts.length > 0
          ? (toolRequestParts as ToolRequestPart[])
          : [
              jsonMode
                ? {
                    data: textContent ? JSON.parse(textContent) : {},
                  }
                : { text: textContent },
            ],
    },
    custom: {},
  };
}

export function toAwsBedrockRequestBody(
  modelName: string,
  request: GenerateRequest<typeof GenerationCommonConfigSchema>,
  inferenceRegion: string
) {
  const model = SUPPORTED_AWS_BEDROCK_MODELS(inferenceRegion)[modelName] || {
    info: {
      supports: {
        output: ['text', 'json'],
        systemRole: true,
        tools: true,
      },
    },
  };
  const awsBedrockMessages = toAwsBedrockMessages(request.messages);

  const awsBedrockSystemMessage = getSystemMessage(request.messages) || [];

  const jsonMode =
    request.output?.format === 'json' ||
    request.output?.contentType === 'application/json';

  const textMode =
    request.output?.format === 'text' ||
    request.output?.contentType === 'plain/text';

  const response_format = request.output?.format
    ? request.output?.format
    : request.output?.contentType;
  if (jsonMode && model.info.supports?.output?.includes('json')) {
    awsBedrockSystemMessage?.push({
      text: 'You write JSON objects based on the given instructions. Please generate only the JSON output. DO NOT provide any preamble.',
    });
  } else if (
    (textMode && model.info.supports?.output?.includes('text')) ||
    model.info.supports?.output?.includes('text')
  ) {
    awsBedrockSystemMessage?.push({
      text: 'You write objects in plain text. DO NOT provide any preamble.',
    });
  } else {
    throw new Error(
      `${response_format} format is not supported for GPT models currently`
    );
  }
  const modelString = (request.config?.version ||
    model.version ||
    modelName) as string;

  const body: ConverseCommandInput | ConverseStreamCommandInput = {
    messages: awsBedrockMessages,
    system:
      model.info.supports.systemRole === true
        ? (awsBedrockSystemMessage as SystemContentBlock[])
        : [],
    toolConfig:
      request.tools &&
      model.info.supports.tools === true &&
      request.tools.length > 0
        ? { tools: request.tools.map(toAwsBedrockTool) }
        : undefined,
    modelId: modelString,
    inferenceConfig: {
      maxTokens: request.config?.maxOutputTokens,
      temperature: request.config?.temperature,
      topP: request.config?.topP,
      //n: request.candidates,
      stopSequences: request.config?.stopSequences,
    },
  };

  return body;
}

export function awsBedrockModel(
  name: string,
  client: BedrockRuntimeClient,
  inferenceRegion: string
): ModelAction<typeof GenerationCommonConfigSchema> {
  const modelId = `aws-bedrock/${name}`;
  const modelReference = SUPPORTED_AWS_BEDROCK_MODELS(inferenceRegion)[name];

  // If model is not in the supported list, create a default configuration
  const modelInfo = modelReference
    ? {
        name: modelId,
        ...modelReference.info,
        configSchema:
          SUPPORTED_AWS_BEDROCK_MODELS(inferenceRegion)[name].configSchema,
      }
    : {
        name: modelId,
        info: {
          label: `AWS Bedrock - ${name}`,
          supports: {
            multiturn: true,
            tools: true,
            media: true,
            systemRole: true,
            output: ['text', 'json'],
          },
        },
        configSchema: GenerationCommonConfigSchema,
      };

  return model(
    modelInfo,
    async (
      request: GenerateRequest<typeof GenerationCommonConfigSchema>,
      {
        streamingRequested,
        sendChunk,
      }: {
        streamingRequested: boolean;
        sendChunk: (chunk: GenerateResponseChunkData) => void;
        abortSignal: AbortSignal;
      }
    ) => {
      let response: ConverseStreamCommandOutput | ConverseCommandOutput;
      const body = toAwsBedrockRequestBody(name, request, inferenceRegion);
      if (streamingRequested) {
        const command = new ConverseStreamCommand(body);
        response = await client.send(command);

        // Accumulate text content from streaming response
        let accumulatedText = '';
        let inputTokens = 0;
        let outputTokens = 0;
        let totalTokens = 0;

        for await (const event of response.stream!) {
          if (event.messageStop) {
            sendChunk({
              index: 0,
              content: [],
            });
          }

          if (event.contentBlockDelta) {
            const delta = event.contentBlockDelta.delta as ContentBlockDelta;
            // Only process text deltas, skip reasoning content deltas
            if (delta && 'text' in delta && delta.text) {
              accumulatedText += delta.text;
              sendChunk({
                index: 0,
                content: [{ text: delta.text }],
              });
            }
          }

          // Capture usage metadata from the stream
          if (event.metadata?.usage) {
            inputTokens = event.metadata.usage.inputTokens || 0;
            outputTokens = event.metadata.usage.outputTokens || 0;
            totalTokens = event.metadata.usage.totalTokens || 0;
          }
        }

        // Return accumulated content for streaming
        const jsonMode = request.output?.format === 'json';
        return {
          message: {
            role: 'model' as const,
            content: [
              jsonMode
                ? { data: accumulatedText ? JSON.parse(accumulatedText) : {} }
                : { text: accumulatedText },
            ],
          },
          usage: {
            inputTokens,
            outputTokens,
            totalTokens,
          },
          custom: response,
        };
      } else {
        const command = new ConverseCommand(body);
        const converseResponse = await client.send(command);

        return {
          message: fromAwsBedrockChoice(
            converseResponse,
            request.output?.format === 'json'
          ).message,
          usage: {
            inputTokens: converseResponse.usage?.inputTokens || 0,
            outputTokens: converseResponse.usage?.outputTokens || 0,
            totalTokens: converseResponse.usage?.totalTokens || 0,
          },
          custom: converseResponse,
        };
      }
    }
  );
}

import Handlebars from 'handlebars';
import { RagasDataPointZodType } from '../types';
import { generate } from '@genkit-ai/ai/generate';
import { Dataset } from '@genkit-ai/ai/evaluators';
import * as z from 'zod';
import { ModelAction, ModelReference } from '@genkit-ai/ai/model';

const contextPrecisionPrompt = `Verify if the information in the given context is useful in answering the question. Here are some examples:

question: What are the health benefits of green tea?
context: 
This article explores the rich history of tea cultivation in China, tracing its roots back to the ancient dynasties. It discusses how different regions have developed their unique tea varieties and brewing techniques. The article also delves into the cultural significance of tea in Chinese society and how it has become a symbol of hospitality and relaxation.
verification:
{"reason":"The context, while informative about the history and cultural significance of tea in China, does not provide specific information about the health benefits of green tea. Thus, it is not useful for answering the question about health benefits.", "verdict":"No"}

question: How does photosynthesis work in plants?
context:
Photosynthesis in plants is a complex process involving multiple steps. This paper details how chlorophyll within the chloroplasts absorbs sunlight, which then drives the chemical reaction converting carbon dioxide and water into glucose and oxygen. It explains the role of light and dark reactions and how ATP and NADPH are produced during these processes.
verification:
{"reason":"This context is extremely relevant and useful for answering the question. It directly addresses the mechanisms of photosynthesis, explaining the key components and processes involved.", "verdict":"Yes"}

Now provide your analysis for the following inputs. DO NOT PROVIDER ANY MORE EXAMPLES. Your response must be a valid JSON like you see above.

question: {{question}}
context: {{context}}
verification:`;

/**
 *
 */
export async function contextPrecisionScore<
  CustomModelOptions extends z.ZodTypeAny
>(
  judgeLlm:
    | ModelAction<CustomModelOptions>
    | ModelReference<CustomModelOptions>,
  dataset: Dataset<RagasDataPointZodType>
) {
  const scores = [] as Array<number>;
  for (const d of dataset) {
    console.debug('sample: ', JSON.stringify(d));
    if (!d.context) {
      throw new Error('context required');
    }
    const promptTemplate = Handlebars.compile(contextPrecisionPrompt);
    const finalPrompt = promptTemplate({
      question: d.input,
      context: d.context.join('\n'),
    });
    const response = await generate({
      model: judgeLlm,
      prompt: finalPrompt,
      output: {
        format: 'json',
        schema: z.object({
          reason: z.string(),
          verdict: z.enum(['Yes', 'No']),
        }),
      },
    });
    scores.push(toScore(response.output()));
  }
  return scores;
}

function toScore(resp: null | { verdict: 'Yes' | 'No'; reason: string }) {
  console.debug('response', resp);
  if (!resp) return 0;
  return resp.verdict === 'Yes' ? 1 : 0;
}

import Handlebars from 'handlebars';
import similarity from 'compute-cosine-similarity';
import * as z from 'zod';
import {
  EmbedderAction,
  EmbedderReference,
  embed,
} from '@google-genkit/ai/embedders';
import { Dataset } from '@google-genkit/ai/evaluators';
import { ModelAction, ModelReference } from '@google-genkit/ai/model';
import { RagasDataPointZodType } from '../types';
import { generate } from '@google-genkit/ai/generate';

const QUESTION_GEN_PROMPT = `Generate a question for the given answer and context. Also identify if answer is noncommittal. Here are some examples:

Answer:
Albert Einstein was born in Germany.
Context:
Albert Einstein was a German-born theoretical physicist who is widely held to be one of the greatest and most influential scientists of all time
Output:
{"question":"Where was Albert Einstein born?","noncommittal":false}


Answer:
It can change its skin color based on the temperature of its environment.
Context:
A recent scientific study has discovered a new species of frog in the Amazon rainforest that has the unique ability to change its skin color based on the temperature of its environment.
Output:
{"question":"What unique ability does the newly discovered species of frog have?","noncommittal":false}


Answer:
Everest
Context:
The tallest mountain on Earth, measured from sea level, is a renowned peak located in the Himalayas.
Output:
{"question":"What is the tallest mountain on Earth?","noncommittal":false}


Answer:
I don't know about the  groundbreaking feature of the smartphone invented in 2023 as am unware of information beyong 2022. 
Context:
In 2023, a groundbreaking invention was announced: a smartphone with a battery life of one month, revolutionizing the way people use mobile technology.
Output:
{"question":"What was the groundbreaking feature of the smartphone invented in 2023?", "noncommittal":true}

Now provide your analysis for the following inputs. DO NOT PROVIDER ANY MORE EXAMPLES. Your response must be a valid JSON like you see above.

Answer:
{{answer}}
Context:
{{context}}
Output:`;

/**
 *
 */
export async function answerRelevancyScore<
  I extends z.ZodTypeAny,
  CustomModelOptions extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(
  judgeLlm:
    | ModelAction<CustomModelOptions>
    | ModelReference<CustomModelOptions>,
  dataset: Dataset<RagasDataPointZodType>,
  embedder:
    | EmbedderAction<I, z.ZodString, EmbedderCustomOptions>
    | EmbedderReference<EmbedderCustomOptions>,
  embedderOptions?: z.infer<EmbedderCustomOptions>
) {
  const scores = [] as Array<number>;
  for (const d of dataset) {
    console.debug('sample: ', JSON.stringify(d));
    if (!d.context || !d.output) {
      throw new Error('contexts and output are required');
    }
    const promptTemplate = Handlebars.compile(QUESTION_GEN_PROMPT);
    const finalPrompt = promptTemplate({
      answer: d.output,
      context: d.context.join(' '),
    });
    const response = await generate({
      model: judgeLlm,
      prompt: finalPrompt,
      output: {
        format: 'json',
        schema: z.object({ question: z.string(), noncommittal: z.boolean() }),
      },
    });
    console.debug('response', response.output());
    const genQuestion = response.output()?.question;
    if (!genQuestion)
      throw new Error('Error generating question for answer relevancy');

    const questionEmbed = await embed({
      embedder,
      input: d.input,
      options: embedderOptions,
    });
    const genQuestionEmbed = await embed({
      embedder,
      input: genQuestion,
      options: embedderOptions,
    });
    const score = cosineSimilarity(questionEmbed, genQuestionEmbed);
    const isNonCommittal = response.output()?.noncommittal ?? false;
    scores.push(score * (isNonCommittal ? 0 : 1));
  }
  return scores;
}

function cosineSimilarity(v1: Array<number>, v2: Array<number>) {
  const maybeScore = similarity(v1, v2);
  if (!maybeScore) {
    throw new Error('Unable to compute cosine similarity');
  }
  return Math.abs(maybeScore);
}

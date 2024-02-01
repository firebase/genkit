import { textModelFactory } from '@google-genkit/ai/text';
import { GoogleGenerativeAI } from '@google/generative-ai';
import process from 'process';
import { z } from 'zod';

const GenaiAiTextModelOptions = z.object({
  // TODO: add me
});

/**
 * Configures a Google Generative AI API Model.
 */
export function configureGenaiAiTextModel(params: {
  apiKey?: string;
  modelName: string;
}) {
  const apiKey = params.apiKey || process.env.GENAI_API_KEY;
  if (!apiKey) {
    throw new Error(
      'please pass in the API key or set GENAI_API_KEY with Google Generative AI API Key'
    );
  }
  const genAI = new GoogleGenerativeAI(apiKey);
  const model = genAI.getGenerativeModel({ model: params.modelName });

  return textModelFactory(
    'google-genai',
    params.modelName,
    GenaiAiTextModelOptions,
    async (input) => {
      const p =
        typeof input.prompt.prompt === 'string' ? input.prompt.prompt : '';
      // TODO: construct proper request, not a lazy
      const result = await model.generateContent(p);
      const response = result.response;
      const text = response.text();

      return {
        completion: text,
        stats: {}, // TODO: fill these out.
      };
    }
  );
}

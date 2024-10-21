import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});


const delegate = ai.defineFlow({
  name: 'delegate',
  description: 'useful to delegate',
}, async () => {
  console.log('delegated')
});


(async () => {
  const chat = await ai.generate({
    prompt: 'call the delegate tool just once',
    tools: [delegate]
  })
  console.log(JSON.stringify(chat.text, undefined, '  '))
})();
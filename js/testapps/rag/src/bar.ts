import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

interface MyState {
  userName: string;
}

const myPrompt2 = ai.definePrompt(
  {
    name: 'myPrompt2',
  },
  async (input) => {
    return {
      messages: [
        {
          role: 'system',
          content: [
            {
              text: `'your name is ${ai.currentSession<MyState>().state?.userName}, always introduce yourself'`,
            },
          ],
        },
      ],
    };
  }
);

const myFlow = ai.defineFlow('myFlow', () => {
  return ai.currentSession<MyState>().state?.userName;
});

(async () => {
  const session = ai.createSession<MyState>({
    initialState: {
      userName: 'Borgle',
    },
  });
  const myPrompt = await ai.prompt('myPrompt2');
  const { text } = await session
    .chat({
      prompt: myPrompt,
    })
    .send('hi');

  console.log(text);

  // run anything that needs access to ai.currentSession()
  console.log(await session.run(() => myFlow()));
})();

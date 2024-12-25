import { gemini15Flash, googleAI } from '@genkit-ai/googleai';
import { genkit } from 'genkit';

(async () => {
  let stream = new ReadableStream({
    start(controller) {
      controller.enqueue(1);
      controller.enqueue(2);
      controller.enqueue(3);
      controller.close();
    },
  });

  const reader = await stream.getReader();

  console.log(await reader.read());
  console.log(await reader.read());
  console.log(await reader.read());
  console.log(await reader.read());
  console.log(await reader.read());
});

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

(async () => {
  const sess = ai.createSession();
  const chat1 = sess.chat({
    messages: [
      {
        role: 'user',
        content: [{ text: 'my name is Bob' }],
      },
      {
        role: 'model',
        content: [{ text: 'hi' }],
      },
    ],
  });
  await chat1.send('what is my name?');
  console.log('- -  --  - - - ', JSON.stringify(chat1.messages, null, 2));

  const chat2 = sess.chat();
  await chat2.send('what is my name?');

  console.log('- -  --  - - - ', JSON.stringify(chat2.messages, null, 2));

  const chat3 = sess.chat({
    messages: [
      {
        role: 'user',
        content: [{ text: 'my name is Jack' }],
      },
      {
        role: 'model',
        content: [{ text: 'hi' }],
      },
    ],
  });
  await chat3.send('what is my name?');

  console.log('- -  --  - - - ', JSON.stringify(chat3.messages, null, 2));
})();

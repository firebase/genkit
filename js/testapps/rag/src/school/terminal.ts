import { createInterface } from 'node:readline';
import { bell, infoAgent } from './school.js';
const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

(async () => {
  const chat = bell.createSession().chat({
    prompt: infoAgent,
  });
  while (true) {
    await new Promise((resolve) => {
      rl.question(`Say: `, async (input) => {
        try {
          const { stream } = await chat.sendStream(input);
          for await (const chunk of stream) {
            process.stdout.write(chunk.text);
          }
          resolve(null);
        } catch (e) {
          console.log('e', e);
        }
      });
    });
  }
})();

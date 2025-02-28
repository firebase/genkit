import { mainFlow } from './flows/mainFlow';

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

let fetching = false;
let promise: Promise<string> | undefined;

function main() {
  while (true) {
    if (promise !== undefined) {
      promise
        .then((result) => {
          console.log(result);
        })
        .catch((err) => {
          console.log(err);
        })
        .finally(() => {
          fetching = false;
        });
    }
    if (fetching === false) {
      console.log('starting to fetch');
      fetching = true;
      console.log('RUNNING FETCHING');
      promise = mainFlow({ imgUrl: 'http://127.0.0.1:8000/frame' });
    }
  }
}

console.log('Hello world');

main();

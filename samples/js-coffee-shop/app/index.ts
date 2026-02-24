
  import { setGenkitRuntimeConfig } from "@genkit-ai/core";
  import {
  greetingWithHistoryFlow,
simpleGreetingFlow,
testAllCoffeeFlows
  } from "/Users/elliothesp/Documents/Development/genkit/samples/js-coffee-shop/src/index.ts";

  setGenkitRuntimeConfig({
    jsonSchemaMode: 'interpret',
    sandboxedRuntime: true,
  });

  export const flows = {
  
    greetingWithHistory: greetingWithHistoryFlow,
      

    simpleGreeting: simpleGreetingFlow,
      

    testAllCoffeeFlows: testAllCoffeeFlows,
      
  };

  // Wrangler requires a default export to treat this as an ES Module worker (so nodejs_compat
  // is applied). This bundle is consumed via the Worker Loader for its `flows` export only;
  // the default export is unused.
  export default { fetch: () => new Response("") };

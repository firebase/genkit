'use strict';
Object.defineProperty(exports, '__esModule', { value: true });
const dotprompt_1 = require('@google-genkit/dotprompt');
const config_1 = require('@google-genkit/common/config');
(0, config_1.initializeGenkit)();
const recipePrompt = (0, dotprompt_1.loadPromptFile)('./recipe.prompt');
recipePrompt
  .generate({ food: process.argv[2] || 'mexican asian fusion' })
  .then((result) => {
    console.log(result.output());
    process.exit(0); // TODO: figure out why process hangs
  })
  .catch(console.error);
//# sourceMappingURL=index.js.map

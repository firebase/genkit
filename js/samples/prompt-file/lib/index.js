"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const dotprompt_1 = require("@genkit-ai/dotprompt");
const config_1 = require("@genkit-ai/common/config");
(0, config_1.initializeGenkit)();
(async () => {
    const food = process.argv[2] || 'mexican asian fusion';
    const recipePrompt = await (0, dotprompt_1.prompt)('recipe');
    const result = await recipePrompt.generate({
        variables: { food },
    });
    console.log(result.output());
    console.log('');
    console.log('Now, as a robot...');
    const robotPrompt = await (0, dotprompt_1.prompt)('recipe', { variant: 'robot' });
    const result2 = await robotPrompt.generate({
        variables: { food },
    });
    console.log(result2.output());
})();
//# sourceMappingURL=index.js.map
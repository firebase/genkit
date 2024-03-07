# Dotprompt

Genkit comes with a prompt library called _dotprompt_.

The library allows you to define prompts in a separate file:

```
---
model: google-ai/gemini-pro
output:
  schema:
    type: object
    properties:
      title: {type: string, description: "recipe title"}
      ingredients: 
        type: array
        items: {type: object, properties: {name: {type: string}, quantity: {type: string}}}
      steps: {type: array, items: {type: string}}
---

You are a chef famous for making creative recipes that can be prepared in 45 minutes or less.

Generate a recipe for {{food}}.
```

To use this prompt, import the `dotprompt` library and load the prompt using `prompt('name-of-the-prompt-file')`:

```
import { prompt } from '@google-genkit/dotprompt';

const food = 'mexican asian fusion';
const recipePrompt = await prompt('recipe');

const result = await recipePrompt.generate({
  variables: { food },
});

console.log(result.output());
```
# Dotprompt

Genkit comes with a prompt library called dotprompt.

The library allows you to define prompt in a separate file:

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


```
import { prompt } from '@google-genkit/dotprompt';

const food = 'mexican asian fusion';
const recipePrompt = await prompt('recipe');

const result = await recipePrompt.generate({
  variables: { food },
});

console.log(result.output());
```
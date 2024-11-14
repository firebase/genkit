# Checks

Checks is an AI safety platform built by Google: [checks.google.com/ai-safety](https://checks.google.com/ai-safety).

This plugin provides evaluators for each Checks AI safety policy. Text is cassified by calling the [Checks Guardrails API](https://console.cloud.google.com/marketplace/product/google/checks.googleapis.com).

> Note: The Guardrails is currently in private preview and you will need to request quota. To request quota fill out this [Google form](https://docs.google.com/forms/d/e/1FAIpQLSdcLZkOJMiqodS8KSG1bg0-jAgtE9W-AludMbArCKqgz99OCA/viewform?usp=sf_link)

Curently that list includes:

```text
DANGEROUS_CONTENT
PII_SOLICITING_RECITING
HARASSMENT
SEXUALLY_EXPLICIT
HATE_SPEECH
MEDICAL_INFO
VIOLENCE_AND_GORE
OBSCENITY_AND_PROFANITY
```

## How to use

### Configure the plugin

Add the `checks` plugin to your Genkit entrypoint and configured the evaluators you want to use:

```ts
import { checks, ChecksEvaluationMetricType } from '@genkit-ai/checks';

export const ai = genkit({
  plugins: [
    checks({
      // Project to charge quota to.
      // Note: If your credentials have a quota project associated with them.
      //       That value will take precedence over this.
      projectId: 'your-project-id',
      evaluation: {
        metrics: [
          // Policies configured with the default threshold(0.5).
          ChecksEvaluationMetricType.DANGEROUS_CONTENT,
          ChecksEvaluationMetricType.HARASSMENT,
          ChecksEvaluationMetricType.HATE_SPEECH,
          ChecksEvaluationMetricType.MEDICAL_INFO,
          ChecksEvaluationMetricType.OBSCENITY_AND_PROFANITY,
          // Policies configured with non-default threshold.
          {
            type: ChecksEvaluationMetricType.PII_SOLICITING_RECITING,
            threshold: 0.6,
          },
          {
            type: ChecksEvaluationMetricType.SEXUALLY_EXPLICIT,
            threshold: 0.3,
          },
          {
            type: ChecksEvaluationMetricType.VIOLENCE_AND_GORE,
            threshold: 0.55,
          },
        ],
      },
    }),
  ],
});
```

### Create a test dataset

Create a JSON file with the data you want to test. Add as many test cases as you want. `output` is the text that will be classified.

```JSON
[
  {
    "testCaseId": "test_case_id_1",
    "input": "The input to your model.",
    "output": "Example model output which. This is what will be evaluated."
  }
]

```

### Run the evaluators

```bash
# Run just the DANGEROUS_CONTENT classifier.
genkit eval:run test-dataset.json --evaluators=checks/dangerous_content
```

```bash
# Run all classifiers.
genkit eval:run test-dataset.json --evaluators=checks/dangerous_content,checks/pii_soliciting_reciting,checks/harassment,checks/sexually_explicit,checks/hate_speech,checks/medical_info,checks/violence_and_gore,checks/obscenity_and_profanity
```

### View the results

Run `genkit start -- tsx --watch src/index.ts` and open the genkit ui. Usually at `localhost:4000` and select the Evaluate tab.

# Genkit

The sources for this package are in the main [Genkit](https://github.com/firebase/genkit) repo. Please file issues and pull requests against that repo.

Usage information and reference details can be found in [Genkit documentation](https://firebase.google.com/docs/genkit).

License: Apache 2.0

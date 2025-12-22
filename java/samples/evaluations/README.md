# Genkit Evaluations Sample

This sample demonstrates how to use Genkit's evaluation framework to assess AI output quality with custom evaluators and datasets.

## Features Demonstrated

- **Custom Evaluators** - Define evaluators for length, keywords, sentiment
- **LLM-Based Evaluators** - Use AI to evaluate AI outputs
- **Datasets** - Create and manage evaluation datasets
- **Evaluation Runs** - Execute evaluations and view results
- **Dev UI Integration** - View evaluations in the Genkit Dev UI

## Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key

## Running the Sample

### Option 1: Direct Run

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/evaluations

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/evaluations

# Run with Genkit CLI
genkit start -- ./run.sh
```

The Dev UI will be available at http://localhost:4000

> **Important**: Run `genkit start` from the same directory where the Java app is running. This ensures the Dev UI can find the datasets stored in `.genkit/datasets/`.

## Available Flows

| Flow | Input | Output | Description |
|------|-------|--------|-------------|
| `describeFood` | String (food) | String | Generate appetizing food descriptions |

## Custom Evaluators

This sample defines several custom evaluators:

| Evaluator | Description |
|-----------|-------------|
| `custom/length` | Checks if output length is between 50-500 characters |
| `custom/keywords` | Checks for food-related descriptive keywords |
| `custom/sentiment` | Evaluates positive/appetizing sentiment |

## Example API Calls

### Describe Food
```bash
curl -X POST http://localhost:8080/describeFood \
  -H 'Content-Type: application/json' \
  -d '"chocolate cake"'
```

## Creating Custom Evaluators

### Simple Rule-Based Evaluator

```java
Evaluator<Void> lengthEvaluator = genkit.defineEvaluator(
    "custom/length",
    "Output Length",
    "Evaluates whether the output has an appropriate length",
    (dataPoint, options) -> {
        String output = dataPoint.getOutput().toString();
        int length = output.length();
        
        double score = (length >= 50 && length <= 500) ? 1.0 : 0.5;
        EvalStatus status = score == 1.0 ? EvalStatus.PASS : EvalStatus.FAIL;
        
        return EvalResponse.builder()
            .testCaseId(dataPoint.getTestCaseId())
            .evaluation(Score.builder()
                .score(score)
                .status(status)
                .reasoning("Output length: " + length)
                .build())
            .build();
    });
```

### Keyword-Based Evaluator

```java
Evaluator<Void> keywordEvaluator = genkit.defineEvaluator(
    "custom/keywords",
    "Food Keywords",
    "Checks for food-related descriptive keywords",
    (dataPoint, options) -> {
        String output = dataPoint.getOutput().toString().toLowerCase();
        
        List<String> keywords = Arrays.asList(
            "delicious", "tasty", "flavor", "savory", "sweet");
        
        int foundCount = 0;
        for (String keyword : keywords) {
            if (output.contains(keyword)) foundCount++;
        }
        
        double score = Math.min(1.0, foundCount / 3.0);
        
        return EvalResponse.builder()
            .testCaseId(dataPoint.getTestCaseId())
            .evaluation(Score.builder()
                .score(score)
                .status(foundCount >= 2 ? EvalStatus.PASS : EvalStatus.FAIL)
                .reasoning("Found " + foundCount + " keywords")
                .build())
            .build();
    });
```

## Working with Datasets

Datasets are stored in `.genkit/datasets/` and can be managed via the Dev UI or programmatically:

```java
// Create a dataset
List<DatasetItem> items = Arrays.asList(
    new DatasetItem("test-1", "pizza", null),
    new DatasetItem("test-2", "sushi", null),
    new DatasetItem("test-3", "tacos", null)
);

// Run evaluation
EvalRunKey result = genkit.evaluate(
    RunEvaluationRequest.builder()
        .datasetId("food-dataset")
        .evaluators(List.of("custom/length", "custom/keywords"))
        .actionRef("/flow/describeFood")
        .build());
```

## Development UI

When running with `genkit start`, access the Dev UI at http://localhost:4000 to:

- Create and manage datasets
- Run evaluations on flows
- View evaluation results and scores
- Compare evaluation runs
- Inspect individual test cases

## Evaluation Results

Evaluation results include:

- **Score**: Numeric value (0.0 - 1.0)
- **Status**: PASS, FAIL, or UNKNOWN
- **Reasoning**: Explanation of the score

## See Also

- [Genkit Java README](../../README.md)
- [Genkit Evaluation Documentation](https://firebase.google.com/docs/genkit/evaluation)

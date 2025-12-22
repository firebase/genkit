/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

package com.google.genkit.samples;

import java.util.*;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.*;
import com.google.genkit.ai.evaluation.*;
import com.google.genkit.core.Flow;
import com.google.genkit.plugins.jetty.JettyPlugin;
import com.google.genkit.plugins.jetty.JettyPluginOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Sample application demonstrating Genkit evaluations, evaluators, and
 * datasets.
 *
 * This example shows how to: - Define custom evaluators - Create and manage
 * datasets - Run evaluations - Use LLM-based evaluators
 *
 * <h2>To run with Dev UI:</h2>
 * <ol>
 * <li>Set the OPENAI_API_KEY environment variable (for LLM-based
 * evaluators)</li>
 * <li>Navigate to the sample directory:
 * {@code cd java/samples/evaluations}</li>
 * <li>Run the app: {@code mvn exec:java}</li>
 * <li>In a separate terminal, from the same directory, run:
 * {@code genkit start}</li>
 * <li>Open the Dev UI at http://localhost:4000</li>
 * </ol>
 *
 * <p>
 * <b>Important:</b> Run {@code genkit start} from the same directory where the
 * Java app is running. This ensures the Dev UI can find the datasets stored in
 * {@code .genkit/datasets/}.
 */
public class EvaluationsSample {

  public static void main(String[] args) throws Exception {
    // Create the Jetty server plugin
    JettyPlugin jetty = new JettyPlugin(JettyPluginOptions.builder().port(8080).build());

    // Create Genkit with plugins
    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).plugin(jetty).build();

    // =====================================================================
    // Define a flow to evaluate
    // =====================================================================

    Flow<String, String, Void> describeFood = genkit.defineFlow("describeFood", String.class, String.class,
        (ctx, food) -> {
          // Use OpenAI to describe the food
          try {
            ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
                .prompt("Describe " + food + " in a delicious and appetizing way in 2-3 sentences.")
                .config(GenerationConfig.builder().temperature(0.8).maxOutputTokens(200).build())
                .build());
            return response.getText();
          } catch (Exception e) {
            return "A delicious " + food + " with wonderful flavors and textures.";
          }
        });

    // =====================================================================
    // Define Custom Evaluators
    // =====================================================================

    // Simple length-based evaluator
    Evaluator<Void> lengthEvaluator = genkit.defineEvaluator("custom/length", "Output Length",
        "Evaluates whether the output has an appropriate length (50-500 characters)", (dataPoint, options) -> {
          String output = dataPoint.getOutput() != null ? dataPoint.getOutput().toString() : "";
          int length = output.length();

          double score;
          EvalStatus status;
          String reasoning;

          if (length >= 50 && length <= 500) {
            score = 1.0;
            status = EvalStatus.PASS;
            reasoning = "Output length (" + length + " chars) is within acceptable range.";
          } else if (length < 50) {
            score = length / 50.0;
            status = EvalStatus.FAIL;
            reasoning = "Output too short (" + length + " chars). Expected at least 50 characters.";
          } else {
            score = Math.max(0, 1.0 - (length - 500) / 500.0);
            status = EvalStatus.FAIL;
            reasoning = "Output too long (" + length + " chars). Expected at most 500 characters.";
          }

          return EvalResponse.builder().testCaseId(dataPoint.getTestCaseId())
              .evaluation(Score.builder().score(score).status(status).reasoning(reasoning).build())
              .build();
        });

    // Keyword presence evaluator
    Evaluator<Void> keywordEvaluator = genkit.defineEvaluator("custom/keywords", "Food Keywords",
        "Checks if the output contains food-related descriptive keywords", (dataPoint, options) -> {
          String output = dataPoint.getOutput() != null ? dataPoint.getOutput().toString().toLowerCase() : "";

          List<String> positiveKeywords = Arrays.asList("delicious", "tasty", "flavor", "savory", "sweet",
              "crispy", "tender", "juicy", "fresh", "aromatic", "rich", "creamy", "satisfying",
              "mouth-watering");

          int foundCount = 0;
          List<String> foundKeywords = new ArrayList<>();
          for (String keyword : positiveKeywords) {
            if (output.contains(keyword)) {
              foundCount++;
              foundKeywords.add(keyword);
            }
          }

          double score = Math.min(1.0, foundCount / 3.0);
          EvalStatus status = foundCount >= 2 ? EvalStatus.PASS : EvalStatus.FAIL;
          String reasoning = "Found " + foundCount + " descriptive keywords: "
              + String.join(", ", foundKeywords);

          return EvalResponse.builder().testCaseId(dataPoint.getTestCaseId())
              .evaluation(Score.builder().score(score).status(status).reasoning(reasoning).build())
              .build();
        });

    // Sentiment evaluator (simple)
    Evaluator<Void> sentimentEvaluator = genkit.defineEvaluator("custom/sentiment", "Positive Sentiment",
        "Evaluates whether the output has a positive/appetizing sentiment", (dataPoint, options) -> {
          String output = dataPoint.getOutput() != null ? dataPoint.getOutput().toString().toLowerCase() : "";

          List<String> positiveWords = Arrays.asList("delicious", "wonderful", "amazing", "excellent",
              "perfect", "lovely", "great", "beautiful", "fantastic", "divine");
          List<String> negativeWords = Arrays.asList("bad", "awful", "terrible", "disgusting", "horrible",
              "gross", "nasty", "unpleasant", "bland");

          int positiveCount = 0;
          int negativeCount = 0;

          for (String word : positiveWords) {
            if (output.contains(word))
              positiveCount++;
          }
          for (String word : negativeWords) {
            if (output.contains(word))
              negativeCount++;
          }

          double sentimentScore = positiveCount - negativeCount;
          double normalizedScore = Math.max(0, Math.min(1, (sentimentScore + 2) / 4.0));

          EvalStatus status = sentimentScore > 0 ? EvalStatus.PASS : EvalStatus.FAIL;
          String reasoning = "Positive words: " + positiveCount + ", Negative words: " + negativeCount;

          return EvalResponse.builder().testCaseId(dataPoint.getTestCaseId())
              .evaluation(
                  Score.builder().score(normalizedScore).status(status).reasoning(reasoning).build())
              .build();
        });

    // LLM-based "Deliciousness" evaluator
    Evaluator<Void> deliciousnessEvaluator = genkit.defineEvaluator("custom/deliciousness", "Deliciousness",
        "Uses an LLM to evaluate how delicious and appetizing the description sounds", true, // isBilled - this
        // evaluator
        // makes LLM
        // calls
        null, (dataPoint, options) -> {
          String output = dataPoint.getOutput() != null ? dataPoint.getOutput().toString() : "";

          try {
            String prompt = """
                You are evaluating how delicious and appetizing a food description sounds.

                Food description to evaluate:
                \"\"\"
                %s
                \"\"\"

                Rate this description on a scale of 0.0 to 1.0 where:
                - 0.0 = Not appetizing at all
                - 0.5 = Somewhat appetizing
                - 1.0 = Extremely appetizing, makes you want to eat it

                Respond with ONLY a JSON object in this format:
                {"score": 0.X, "reasoning": "brief explanation"}
                """.formatted(output);

            ModelResponse response = genkit.generate(GenerateOptions.builder().model("openai/gpt-4o-mini")
                .prompt(prompt)
                .config(GenerationConfig.builder().temperature(0.0).maxOutputTokens(200).build())
                .build());

            String responseText = response.getText().trim();
            // Parse the JSON response
            // Simple parsing - in production you'd use a JSON parser
            double score = 0.5;
            String reasoning = "Unable to parse response";

            if (responseText.contains("\"score\"")) {
              int scoreStart = responseText.indexOf("\"score\"") + 9;
              int scoreEnd = responseText.indexOf(",", scoreStart);
              if (scoreEnd == -1)
                scoreEnd = responseText.indexOf("}", scoreStart);
              try {
                score = Double.parseDouble(responseText.substring(scoreStart, scoreEnd).trim());
              } catch (NumberFormatException e) {
                // Keep default
              }
            }
            if (responseText.contains("\"reasoning\"")) {
              int reasonStart = responseText.indexOf("\"reasoning\"") + 13;
              int reasonEnd = responseText.lastIndexOf("\"");
              if (reasonEnd > reasonStart) {
                reasoning = responseText.substring(reasonStart, reasonEnd);
              }
            }

            return EvalResponse.builder().testCaseId(dataPoint.getTestCaseId())
                .evaluation(Score.builder().score(score)
                    .status(score >= 0.6 ? EvalStatus.PASS : EvalStatus.FAIL).reasoning(reasoning)
                    .build())
                .build();

          } catch (Exception e) {
            return EvalResponse.builder().testCaseId(dataPoint.getTestCaseId()).evaluation(Score.builder()
                .error("Failed to evaluate: " + e.getMessage()).status(EvalStatus.UNKNOWN).build())
                .build();
          }
        });

    // =====================================================================
    // Create a Sample Dataset
    // =====================================================================

    DatasetStore datasetStore = genkit.getDatasetStore();

    // Check if our sample dataset already exists
    List<DatasetMetadata> existingDatasets = datasetStore.listDatasets();
    boolean datasetExists = existingDatasets.stream().anyMatch(d -> "food_descriptions".equals(d.getDatasetId()));

    if (!datasetExists) {
      // Create the sample dataset
      List<DatasetSample> samples = Arrays.asList(
          DatasetSample.builder().testCaseId("food_1").input("pizza").reference(
              "A delicious Italian dish with a crispy crust, tangy tomato sauce, and melted cheese.")
              .build(),
          DatasetSample.builder().testCaseId("food_2").input("sushi")
              .reference("Fresh, delicate rolls of vinegared rice with raw fish and vegetables.").build(),
          DatasetSample.builder().testCaseId("food_3").input("tacos").reference(
              "Flavorful Mexican street food with seasoned meat, fresh salsa, and corn tortillas.")
              .build(),
          DatasetSample.builder().testCaseId("food_4").input("chocolate cake")
              .reference("Rich, moist layers of chocolate with creamy frosting.").build(),
          DatasetSample.builder().testCaseId("food_5").input("ramen").reference(
              "A comforting bowl of noodles in savory broth with tender pork and soft-boiled egg.")
              .build());

      CreateDatasetRequest createRequest = CreateDatasetRequest.builder().datasetId("food_descriptions")
          .data(samples).datasetType(DatasetType.FLOW).targetAction("/flow/describeFood").metricRefs(Arrays
              .asList("custom/length", "custom/keywords", "custom/sentiment", "custom/deliciousness"))
          .build();

      DatasetMetadata metadata = datasetStore.createDataset(createRequest);
      System.out.println(
          "Created dataset: " + metadata.getDatasetId() + " with " + metadata.getSize() + " samples");
    } else {
      System.out.println("Dataset 'food_descriptions' already exists");
    }

    // =====================================================================
    // Define a flow to run evaluations programmatically
    // =====================================================================

    Flow<String, Map<String, Object>, Void> runEvaluationFlow = genkit.defineFlow("runEvaluation", String.class,
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, datasetId) -> {
          try {
            // Create evaluation request
            RunEvaluationRequest.DataSource dataSource = new RunEvaluationRequest.DataSource();
            dataSource.setDatasetId(datasetId);

            RunEvaluationRequest request = RunEvaluationRequest.builder().dataSource(dataSource)
                .targetAction("/flow/describeFood")
                .evaluators(Arrays.asList("custom/length", "custom/keywords", "custom/sentiment"))
                .build();

            EvalRunKey evalRunKey = genkit.evaluate(request);

            // Return the result
            Map<String, Object> result = new HashMap<>();
            result.put("evalRunId", evalRunKey.getEvalRunId());
            result.put("createdAt", evalRunKey.getCreatedAt());
            result.put("datasetId", datasetId);
            return result;
          } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return error;
          }
        });

    // =====================================================================
    // Print Information
    // =====================================================================

    System.out.println();
    System.out.println("╔══════════════════════════════════════════════════════════════════╗");
    System.out.println("║           Genkit Evaluations Sample Application                  ║");
    System.out.println("╠══════════════════════════════════════════════════════════════════╣");
    System.out.println("║ Dev UI: http://localhost:3100                                    ║");
    System.out.println("╠══════════════════════════════════════════════════════════════════╣");
    System.out.println("║ Registered Evaluators:                                           ║");
    System.out.println("║   • custom/length      - Checks output length (50-500 chars)     ║");
    System.out.println("║   • custom/keywords    - Checks for food-related keywords        ║");
    System.out.println("║   • custom/sentiment   - Evaluates positive sentiment            ║");
    System.out.println("║   • custom/deliciousness - LLM-based appetizing evaluation       ║");
    System.out.println("╠══════════════════════════════════════════════════════════════════╣");
    System.out.println("║ API Endpoints:                                                   ║");
    System.out.println("║   POST /api/flows/describeFood  - Describe a food item          ║");
    System.out.println("║   POST /api/flows/runEvaluation - Run evaluation on dataset     ║");
    System.out.println("║   GET  /api/datasets            - List all datasets              ║");
    System.out.println("║   GET  /api/evalRuns            - List evaluation runs           ║");
    System.out.println("╠══════════════════════════════════════════════════════════════════╣");
    System.out.println("║ Example usage:                                                   ║");
    System.out.println("║   curl -X POST http://localhost:8080/api/flows/describeFood \\   ║");
    System.out.println("║        -d '\"pizza\"' -H 'Content-Type: application/json'         ║");
    System.out.println("║                                                                  ║");
    System.out.println("║   curl -X POST http://localhost:8080/api/flows/runEvaluation \\  ║");
    System.out.println("║        -d '\"food_descriptions\"' -H 'Content-Type: application/json'║");
    System.out.println("╠══════════════════════════════════════════════════════════════════╣");
    System.out.println("║ Data Storage:                                                    ║");
    System.out.println("║   Datasets: ./.genkit/datasets/                                  ║");
    System.out.println("║   Eval Runs: ./.genkit/evals/                                    ║");
    System.out.println("╠══════════════════════════════════════════════════════════════════╣");
    System.out.println("║ IMPORTANT: To see datasets in Dev UI, run 'genkit start' from   ║");
    System.out.println("║ the SAME directory where this app runs (current working dir).   ║");
    System.out.println("╚══════════════════════════════════════════════════════════════════╝");
    System.out.println();
    System.out.println("Working directory: " + System.getProperty("user.dir"));
    System.out.println();
    System.out.println("Press Ctrl+C to stop...");

    // Start the server and block
    jetty.start();
  }
}

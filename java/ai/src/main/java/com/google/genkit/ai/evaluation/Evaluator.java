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

package com.google.genkit.ai.evaluation;

import java.util.*;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.google.genkit.core.*;

/**
 * Evaluator represents an evaluation action that assesses the quality of AI
 * outputs.
 * 
 * <p>
 * Evaluators are a core primitive in Genkit that allow you to measure and track
 * the quality of your AI applications. They can be used to:
 * <ul>
 * <li>Score outputs based on various criteria (accuracy, relevance, etc.)</li>
 * <li>Compare outputs against reference data</li>
 * <li>Run automated quality checks in CI/CD pipelines</li>
 * <li>Monitor production quality over time</li>
 * </ul>
 *
 * @param <O>
 *            the type of evaluator-specific options
 */
public class Evaluator<O> implements Action<EvalRequest, List<EvalResponse>, Void> {

  private static final Logger logger = LoggerFactory.getLogger(Evaluator.class);

  public static final String METADATA_KEY_DISPLAY_NAME = "evaluatorDisplayName";
  public static final String METADATA_KEY_DEFINITION = "evaluatorDefinition";
  public static final String METADATA_KEY_IS_BILLED = "evaluatorIsBilled";

  private final String name;
  private final EvaluatorInfo info;
  private final EvaluatorFn<O> evaluatorFn;
  private final Class<O> optionsClass;
  private final ActionDesc desc;

  private Evaluator(Builder<O> builder) {
    this.name = builder.name;
    this.info = EvaluatorInfo.builder().displayName(builder.displayName).definition(builder.definition)
        .isBilled(builder.isBilled).build();
    this.evaluatorFn = builder.evaluatorFn;
    this.optionsClass = builder.optionsClass;

    // Build metadata
    Map<String, Object> metadata = new HashMap<>();
    metadata.put("type", "evaluator");
    Map<String, Object> evaluatorMetadata = new HashMap<>();
    evaluatorMetadata.put(METADATA_KEY_DISPLAY_NAME, builder.displayName);
    evaluatorMetadata.put(METADATA_KEY_DEFINITION, builder.definition);
    evaluatorMetadata.put(METADATA_KEY_IS_BILLED, builder.isBilled);
    metadata.put("evaluator", evaluatorMetadata);

    this.desc = ActionDesc.builder().type(ActionType.EVALUATOR).name(name).description(builder.definition)
        .metadata(metadata).build();
  }

  /**
   * Creates a new Evaluator builder.
   *
   * @param <O>
   *            the options type
   * @return a new builder
   */
  public static <O> Builder<O> builder() {
    return new Builder<>();
  }

  /**
   * Defines a new evaluator and registers it with the registry.
   *
   * @param <O>
   *            the options type
   * @param registry
   *            the registry to register with
   * @param name
   *            the evaluator name
   * @param displayName
   *            the display name shown in the UI
   * @param definition
   *            description of what the evaluator measures
   * @param evaluatorFn
   *            the evaluation function
   * @return the created evaluator
   */
  public static <O> Evaluator<O> define(Registry registry, String name, String displayName, String definition,
      EvaluatorFn<O> evaluatorFn) {
    return define(registry, name, displayName, definition, true, null, evaluatorFn);
  }

  /**
   * Defines a new evaluator with full options and registers it with the registry.
   *
   * @param <O>
   *            the options type
   * @param registry
   *            the registry to register with
   * @param name
   *            the evaluator name
   * @param displayName
   *            the display name shown in the UI
   * @param definition
   *            description of what the evaluator measures
   * @param isBilled
   *            whether using this evaluator incurs costs
   * @param optionsClass
   *            the class for evaluator-specific options
   * @param evaluatorFn
   *            the evaluation function
   * @return the created evaluator
   */
  public static <O> Evaluator<O> define(Registry registry, String name, String displayName, String definition,
      boolean isBilled, Class<O> optionsClass, EvaluatorFn<O> evaluatorFn) {

    Evaluator<O> evaluator = Evaluator.<O>builder().name(name).displayName(displayName).definition(definition)
        .isBilled(isBilled).optionsClass(optionsClass).evaluatorFn(evaluatorFn).build();

    evaluator.register(registry);
    return evaluator;
  }

  @Override
  public String getName() {
    return name;
  }

  @Override
  public ActionType getType() {
    return ActionType.EVALUATOR;
  }

  @Override
  public ActionDesc getDesc() {
    return desc;
  }

  /**
   * Gets the evaluator info.
   *
   * @return the evaluator info
   */
  public EvaluatorInfo getInfo() {
    return info;
  }

  @Override
  public List<EvalResponse> run(ActionContext ctx, EvalRequest input) throws GenkitException {
    return run(ctx, input, null);
  }

  @Override
  public List<EvalResponse> run(ActionContext ctx, EvalRequest input, Consumer<Void> streamCallback)
      throws GenkitException {
    List<EvalResponse> responses = new ArrayList<>();
    List<EvalDataPoint> dataset = input.getDataset();

    if (dataset == null || dataset.isEmpty()) {
      return responses;
    }

    int batchSize = input.getBatchSize() != null ? input.getBatchSize() : 10;

    // Process in batches
    List<List<EvalDataPoint>> batches = batchList(dataset, batchSize);
    int sampleIndex = 0;

    for (List<EvalDataPoint> batch : batches) {
      for (EvalDataPoint dataPoint : batch) {
        try {
          @SuppressWarnings("unchecked")
          O options = input.getOptions() != null && optionsClass != null
              ? JsonUtils.getObjectMapper().convertValue(input.getOptions(), optionsClass)
              : null;

          EvalResponse response = evaluatorFn.evaluate(dataPoint, options);
          if (response.getSampleIndex() == null) {
            response.setSampleIndex(sampleIndex);
          }
          responses.add(response);
        } catch (Exception e) {
          logger.error("Error evaluating data point: {}", dataPoint.getTestCaseId(), e);
          // Create an error response
          Score errorScore = Score.builder().error(e.getMessage()).status(EvalStatus.UNKNOWN).build();
          responses.add(EvalResponse.builder().testCaseId(dataPoint.getTestCaseId()).sampleIndex(sampleIndex)
              .evaluation(errorScore).build());
        }
        sampleIndex++;
      }
    }

    return responses;
  }

  @Override
  public JsonNode runJson(ActionContext ctx, JsonNode input, Consumer<JsonNode> streamCallback)
      throws GenkitException {
    EvalRequest request = JsonUtils.fromJsonNode(input, EvalRequest.class);
    List<EvalResponse> result = run(ctx, request, null);
    return JsonUtils.toJsonNode(result);
  }

  @Override
  public ActionRunResult<JsonNode> runJsonWithTelemetry(ActionContext ctx, JsonNode input,
      Consumer<JsonNode> streamCallback) throws GenkitException {
    JsonNode result = runJson(ctx, input, streamCallback);
    return new ActionRunResult<>(result, null, null);
  }

  @Override
  public void register(Registry registry) {
    String key = ActionType.EVALUATOR.keyFromName(name);
    registry.registerAction(key, this);
    logger.info("Registered evaluator: {}", key);
  }

  @Override
  public Map<String, Object> getInputSchema() {
    // Define the input schema for EvalRequest
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "object");

    Map<String, Object> properties = new HashMap<>();

    // dataset property
    Map<String, Object> datasetProp = new HashMap<>();
    datasetProp.put("type", "array");
    Map<String, Object> dataPointSchema = new HashMap<>();
    dataPointSchema.put("type", "object");
    datasetProp.put("items", dataPointSchema);
    properties.put("dataset", datasetProp);

    // evalRunId property
    Map<String, Object> evalRunIdProp = new HashMap<>();
    evalRunIdProp.put("type", "string");
    properties.put("evalRunId", evalRunIdProp);

    // batchSize property
    Map<String, Object> batchSizeProp = new HashMap<>();
    batchSizeProp.put("type", "integer");
    properties.put("batchSize", batchSizeProp);

    schema.put("properties", properties);
    schema.put("required", Arrays.asList("dataset"));

    return schema;
  }

  @Override
  public Map<String, Object> getOutputSchema() {
    // Define the output schema for List<EvalResponse>
    Map<String, Object> schema = new HashMap<>();
    schema.put("type", "array");

    Map<String, Object> itemSchema = new HashMap<>();
    itemSchema.put("type", "object");

    Map<String, Object> itemProps = new HashMap<>();

    // testCaseId
    Map<String, Object> testCaseIdProp = new HashMap<>();
    testCaseIdProp.put("type", "string");
    itemProps.put("testCaseId", testCaseIdProp);

    // evaluation (Score)
    Map<String, Object> evaluationProp = new HashMap<>();
    evaluationProp.put("type", "object");
    itemProps.put("evaluation", evaluationProp);

    itemSchema.put("properties", itemProps);
    schema.put("items", itemSchema);

    return schema;
  }

  @Override
  public Map<String, Object> getMetadata() {
    return desc.getMetadata();
  }

  /**
   * Splits a list into batches.
   */
  private static <T> List<List<T>> batchList(List<T> list, int batchSize) {
    List<List<T>> batches = new ArrayList<>();
    for (int i = 0; i < list.size(); i += batchSize) {
      batches.add(list.subList(i, Math.min(i + batchSize, list.size())));
    }
    return batches;
  }

  /**
   * Builder for creating Evaluator instances.
   *
   * @param <O>
   *            the options type
   */
  public static class Builder<O> {
    private String name;
    private String displayName;
    private String definition;
    private boolean isBilled = true;
    private Class<O> optionsClass;
    private EvaluatorFn<O> evaluatorFn;

    public Builder<O> name(String name) {
      this.name = name;
      return this;
    }

    public Builder<O> displayName(String displayName) {
      this.displayName = displayName;
      return this;
    }

    public Builder<O> definition(String definition) {
      this.definition = definition;
      return this;
    }

    public Builder<O> isBilled(boolean isBilled) {
      this.isBilled = isBilled;
      return this;
    }

    public Builder<O> optionsClass(Class<O> optionsClass) {
      this.optionsClass = optionsClass;
      return this;
    }

    public Builder<O> evaluatorFn(EvaluatorFn<O> evaluatorFn) {
      this.evaluatorFn = evaluatorFn;
      return this;
    }

    public Evaluator<O> build() {
      if (name == null || name.isEmpty()) {
        throw new IllegalArgumentException("Evaluator name is required");
      }
      if (displayName == null) {
        displayName = name;
      }
      if (definition == null) {
        definition = "";
      }
      if (evaluatorFn == null) {
        throw new IllegalArgumentException("Evaluator function is required");
      }
      return new Evaluator<>(this);
    }
  }
}

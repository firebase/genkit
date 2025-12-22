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

import java.time.Instant;
import java.util.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.core.*;

/**
 * Manages the execution of evaluations.
 * 
 * <p>
 * The EvaluationManager coordinates running evaluations by:
 * <ul>
 * <li>Loading datasets from the dataset store</li>
 * <li>Running inference on the target action</li>
 * <li>Executing evaluators on the results</li>
 * <li>Storing evaluation results</li>
 * </ul>
 */
public class EvaluationManager {

  private static final Logger logger = LoggerFactory.getLogger(EvaluationManager.class);

  private final Registry registry;
  private final DatasetStore datasetStore;
  private final EvalStore evalStore;

  /**
   * Creates a new EvaluationManager.
   *
   * @param registry
   *            the Genkit registry
   */
  public EvaluationManager(Registry registry) {
    this(registry, LocalFileDatasetStore.getInstance(), LocalFileEvalStore.getInstance());
  }

  /**
   * Creates a new EvaluationManager with custom stores.
   *
   * @param registry
   *            the Genkit registry
   * @param datasetStore
   *            the dataset store
   * @param evalStore
   *            the eval store
   */
  public EvaluationManager(Registry registry, DatasetStore datasetStore, EvalStore evalStore) {
    this.registry = registry;
    this.datasetStore = datasetStore;
    this.evalStore = evalStore;
  }

  /**
   * Runs a new evaluation.
   *
   * @param request
   *            the evaluation request
   * @return the evaluation run key
   * @throws Exception
   *             if evaluation fails
   */
  public EvalRunKey runEvaluation(RunEvaluationRequest request) throws Exception {
    String evalRunId = UUID.randomUUID().toString();
    String actionRef = request.getTargetAction();

    // 1. Load or parse dataset
    List<DatasetSample> dataset;
    String datasetId = null;
    Integer datasetVersion = null;

    if (request.getDataSource().getDatasetId() != null) {
      datasetId = request.getDataSource().getDatasetId();
      dataset = datasetStore.getDataset(datasetId);
      List<DatasetMetadata> metadataList = datasetStore.listDatasets();
      for (DatasetMetadata m : metadataList) {
        if (m.getDatasetId().equals(datasetId)) {
          datasetVersion = m.getVersion();
          break;
        }
      }
    } else {
      dataset = request.getDataSource().getData();
    }

    if (dataset == null || dataset.isEmpty()) {
      throw new IllegalArgumentException("Dataset is empty");
    }

    // Ensure all samples have testCaseIds
    for (int i = 0; i < dataset.size(); i++) {
      DatasetSample sample = dataset.get(i);
      if (sample.getTestCaseId() == null) {
        sample.setTestCaseId("test_case_" + (i + 1));
      }
    }

    // 2. Run inference on the target action
    List<EvalDataPoint> evalDataset = runInference(actionRef, dataset, request.getOptions());

    // 3. Get matching evaluator actions
    List<String> evaluatorNames = request.getEvaluators();
    if (evaluatorNames == null || evaluatorNames.isEmpty()) {
      // Get all evaluators
      evaluatorNames = getAllEvaluatorNames();
    }

    // 4. Run evaluation
    Map<String, List<EvalResponse>> allScores = new HashMap<>();
    int batchSize = request.getOptions() != null && request.getOptions().getBatchSize() != null
        ? request.getOptions().getBatchSize()
        : 10;

    for (String evaluatorName : evaluatorNames) {
      String evalKey = ActionType.EVALUATOR.keyFromName(evaluatorName);
      Action<?, ?, ?> evaluatorAction = registry.lookupAction(evalKey);

      if (evaluatorAction == null) {
        logger.warn("Evaluator not found: {}", evaluatorName);
        continue;
      }

      try {
        // Filter out data points with errors
        List<EvalDataPoint> validDataPoints = new ArrayList<>();
        for (EvalDataPoint dp : evalDataset) {
          if (dp.getError() == null) {
            validDataPoints.add(dp);
          }
        }

        EvalRequest evalRequest = EvalRequest.builder().dataset(validDataPoints).evalRunId(evalRunId)
            .batchSize(batchSize).build();

        ActionContext ctx = new ActionContext(registry);
        @SuppressWarnings("unchecked")
        List<EvalResponse> responses = ((Action<EvalRequest, List<EvalResponse>, ?>) evaluatorAction).run(ctx,
            evalRequest);

        allScores.put(evaluatorName, responses);
      } catch (Exception e) {
        logger.error("Error running evaluator: {}", evaluatorName, e);
      }
    }

    // 5. Combine scores with dataset
    List<EvalResult> results = combineResults(evalDataset, allScores);

    // 6. Create and save eval run
    EvalRunKey key = EvalRunKey.builder().evalRunId(evalRunId).actionRef(actionRef).datasetId(datasetId)
        .datasetVersion(datasetVersion).createdAt(Instant.now().toString())
        .actionConfig(request.getOptions() != null ? request.getOptions().getActionConfig() : null).build();

    EvalRun evalRun = EvalRun.builder().key(key).results(results).build();

    evalStore.save(evalRun);

    logger.info("Completed evaluation run: {} with {} results", evalRunId, results.size());
    return key;
  }

  /**
   * Runs inference on the target action for all dataset samples.
   */
  private List<EvalDataPoint> runInference(String actionRef, List<DatasetSample> dataset,
      RunEvaluationRequest.EvaluationOptions options) {

    List<EvalDataPoint> evalDataset = new ArrayList<>();
    Action<?, ?, ?> action = registry.lookupAction(actionRef);

    for (DatasetSample sample : dataset) {
      EvalDataPoint.Builder dpBuilder = EvalDataPoint.builder().testCaseId(sample.getTestCaseId())
          .input(sample.getInput()).reference(sample.getReference()).traceIds(new ArrayList<>());

      if (action != null) {
        try {
          ActionContext ctx = new ActionContext(registry);
          Object input = sample.getInput();

          @SuppressWarnings("unchecked")
          Object output = ((Action<Object, Object, ?>) action).run(ctx, input);
          dpBuilder.output(output);
        } catch (Exception e) {
          logger.error("Error running inference for test case: {}", sample.getTestCaseId(), e);
          dpBuilder.error(e.getMessage());
        }
      } else {
        logger.warn("Action not found: {}. Using input as output.", actionRef);
        dpBuilder.output(sample.getInput());
      }

      evalDataset.add(dpBuilder.build());
    }

    return evalDataset;
  }

  /**
   * Gets all registered evaluator names.
   */
  private List<String> getAllEvaluatorNames() {
    List<String> names = new ArrayList<>();
    for (Action<?, ?, ?> action : registry.listActions()) {
      if (action.getType() == ActionType.EVALUATOR) {
        names.add(action.getName());
      }
    }
    return names;
  }

  /**
   * Combines evaluation results with scores from all evaluators.
   */
  private List<EvalResult> combineResults(List<EvalDataPoint> evalDataset,
      Map<String, List<EvalResponse>> allScores) {

    // Create a map of testCaseId to EvalResult
    Map<String, EvalResult.Builder> resultBuilders = new LinkedHashMap<>();

    for (EvalDataPoint dp : evalDataset) {
      resultBuilders.put(dp.getTestCaseId(),
          EvalResult.builder().testCaseId(dp.getTestCaseId()).input(dp.getInput()).output(dp.getOutput())
              .error(dp.getError()).context(dp.getContext()).reference(dp.getReference())
              .traceIds(dp.getTraceIds()).metrics(new ArrayList<>()));
    }

    // Add scores from each evaluator
    for (Map.Entry<String, List<EvalResponse>> entry : allScores.entrySet()) {
      String evaluatorName = entry.getKey();

      for (EvalResponse response : entry.getValue()) {
        EvalResult.Builder builder = resultBuilders.get(response.getTestCaseId());
        if (builder == null) {
          continue;
        }

        Object evaluation = response.getEvaluation();
        if (evaluation instanceof Score) {
          Score score = (Score) evaluation;
          EvalMetric metric = scoreToMetric(evaluatorName, score, response);
          // Need to build, modify, and rebuild since metrics is already set
          EvalResult temp = builder.build();
          temp.getMetrics().add(metric);
        } else if (evaluation instanceof List) {
          @SuppressWarnings("unchecked")
          List<Score> scores = (List<Score>) evaluation;
          for (Score score : scores) {
            EvalMetric metric = scoreToMetric(evaluatorName, score, response);
            EvalResult temp = builder.build();
            temp.getMetrics().add(metric);
          }
        }
      }
    }

    List<EvalResult> results = new ArrayList<>();
    for (EvalResult.Builder builder : resultBuilders.values()) {
      results.add(builder.build());
    }
    return results;
  }

  private EvalMetric scoreToMetric(String evaluatorName, Score score, EvalResponse response) {
    String rationale = null;
    if (score.getDetails() != null) {
      rationale = score.getDetails().getReasoning();
    }

    return EvalMetric.builder().evaluator(evaluatorName).scoreId(score.getId()).score(score.getScore())
        .status(score.getStatus()).rationale(rationale).error(score.getError()).traceId(response.getTraceId())
        .spanId(response.getSpanId()).build();
  }

  /**
   * Gets the dataset store.
   */
  public DatasetStore getDatasetStore() {
    return datasetStore;
  }

  /**
   * Gets the eval store.
   */
  public EvalStore getEvalStore() {
    return evalStore;
  }
}

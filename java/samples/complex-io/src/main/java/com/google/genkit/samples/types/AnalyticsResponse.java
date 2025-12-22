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

package com.google.genkit.samples.types;

import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Complex analytics response with multiple data visualizations.
 */
public class AnalyticsResponse {

  @JsonProperty("requestId")
  private String requestId;

  @JsonProperty("executionTime")
  private String executionTime;

  @JsonProperty("summary")
  private Summary summary;

  @JsonProperty("data")
  private DataResult data;

  @JsonProperty("visualizations")
  private List<Visualization> visualizations;

  @JsonProperty("insights")
  private List<Insight> insights;

  @JsonProperty("metadata")
  private ResponseMetadata metadata;

  // Nested types
  public static class Summary {
    @JsonProperty("totalRecords")
    private Long totalRecords;

    @JsonProperty("metrics")
    private Map<String, MetricValue> metrics;

    @JsonProperty("trends")
    private List<TrendIndicator> trends;

    // Getters and setters
    public Long getTotalRecords() {
      return totalRecords;
    }
    public void setTotalRecords(Long totalRecords) {
      this.totalRecords = totalRecords;
    }
    public Map<String, MetricValue> getMetrics() {
      return metrics;
    }
    public void setMetrics(Map<String, MetricValue> metrics) {
      this.metrics = metrics;
    }
    public List<TrendIndicator> getTrends() {
      return trends;
    }
    public void setTrends(List<TrendIndicator> trends) {
      this.trends = trends;
    }
  }

  public static class MetricValue {
    @JsonProperty("value")
    private Object value;

    @JsonProperty("formatted")
    private String formatted;

    @JsonProperty("change")
    private ChangeIndicator change;

    // Getters and setters
    public Object getValue() {
      return value;
    }
    public void setValue(Object value) {
      this.value = value;
    }
    public String getFormatted() {
      return formatted;
    }
    public void setFormatted(String formatted) {
      this.formatted = formatted;
    }
    public ChangeIndicator getChange() {
      return change;
    }
    public void setChange(ChangeIndicator change) {
      this.change = change;
    }
  }

  public static class ChangeIndicator {
    @JsonProperty("absolute")
    private Double absolute;

    @JsonProperty("percentage")
    private Double percentage;

    @JsonProperty("direction")
    private String direction; // up, down, stable

    @JsonProperty("comparisonPeriod")
    private String comparisonPeriod;

    // Getters and setters
    public Double getAbsolute() {
      return absolute;
    }
    public void setAbsolute(Double absolute) {
      this.absolute = absolute;
    }
    public Double getPercentage() {
      return percentage;
    }
    public void setPercentage(Double percentage) {
      this.percentage = percentage;
    }
    public String getDirection() {
      return direction;
    }
    public void setDirection(String direction) {
      this.direction = direction;
    }
    public String getComparisonPeriod() {
      return comparisonPeriod;
    }
    public void setComparisonPeriod(String comparisonPeriod) {
      this.comparisonPeriod = comparisonPeriod;
    }
  }

  public static class TrendIndicator {
    @JsonProperty("metric")
    private String metric;

    @JsonProperty("trend")
    private String trend;

    @JsonProperty("confidence")
    private Double confidence;

    @JsonProperty("forecast")
    private List<ForecastPoint> forecast;

    // Getters and setters
    public String getMetric() {
      return metric;
    }
    public void setMetric(String metric) {
      this.metric = metric;
    }
    public String getTrend() {
      return trend;
    }
    public void setTrend(String trend) {
      this.trend = trend;
    }
    public Double getConfidence() {
      return confidence;
    }
    public void setConfidence(Double confidence) {
      this.confidence = confidence;
    }
    public List<ForecastPoint> getForecast() {
      return forecast;
    }
    public void setForecast(List<ForecastPoint> forecast) {
      this.forecast = forecast;
    }
  }

  public static class ForecastPoint {
    @JsonProperty("date")
    private String date;

    @JsonProperty("value")
    private Double value;

    @JsonProperty("lower")
    private Double lower;

    @JsonProperty("upper")
    private Double upper;

    // Getters and setters
    public String getDate() {
      return date;
    }
    public void setDate(String date) {
      this.date = date;
    }
    public Double getValue() {
      return value;
    }
    public void setValue(Double value) {
      this.value = value;
    }
    public Double getLower() {
      return lower;
    }
    public void setLower(Double lower) {
      this.lower = lower;
    }
    public Double getUpper() {
      return upper;
    }
    public void setUpper(Double upper) {
      this.upper = upper;
    }
  }

  public static class DataResult {
    @JsonProperty("columns")
    private List<ColumnDefinition> columns;

    @JsonProperty("rows")
    private List<Map<String, Object>> rows;

    @JsonProperty("aggregations")
    private Map<String, Object> aggregations;

    // Getters and setters
    public List<ColumnDefinition> getColumns() {
      return columns;
    }
    public void setColumns(List<ColumnDefinition> columns) {
      this.columns = columns;
    }
    public List<Map<String, Object>> getRows() {
      return rows;
    }
    public void setRows(List<Map<String, Object>> rows) {
      this.rows = rows;
    }
    public Map<String, Object> getAggregations() {
      return aggregations;
    }
    public void setAggregations(Map<String, Object> aggregations) {
      this.aggregations = aggregations;
    }
  }

  public static class ColumnDefinition {
    @JsonProperty("name")
    private String name;

    @JsonProperty("type")
    private String type;

    @JsonProperty("format")
    private String format;

    @JsonProperty("aggregation")
    private String aggregation;

    // Getters and setters
    public String getName() {
      return name;
    }
    public void setName(String name) {
      this.name = name;
    }
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public String getFormat() {
      return format;
    }
    public void setFormat(String format) {
      this.format = format;
    }
    public String getAggregation() {
      return aggregation;
    }
    public void setAggregation(String aggregation) {
      this.aggregation = aggregation;
    }
  }

  public static class Visualization {
    @JsonProperty("id")
    private String id;

    @JsonProperty("type")
    private String type; // line, bar, pie, scatter, heatmap, table

    @JsonProperty("title")
    private String title;

    @JsonProperty("data")
    private VisualizationData data;

    @JsonProperty("config")
    private VisualizationConfig config;

    // Getters and setters
    public String getId() {
      return id;
    }
    public void setId(String id) {
      this.id = id;
    }
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public String getTitle() {
      return title;
    }
    public void setTitle(String title) {
      this.title = title;
    }
    public VisualizationData getData() {
      return data;
    }
    public void setData(VisualizationData data) {
      this.data = data;
    }
    public VisualizationConfig getConfig() {
      return config;
    }
    public void setConfig(VisualizationConfig config) {
      this.config = config;
    }
  }

  public static class VisualizationData {
    @JsonProperty("labels")
    private List<String> labels;

    @JsonProperty("datasets")
    private List<Dataset> datasets;

    // Getters and setters
    public List<String> getLabels() {
      return labels;
    }
    public void setLabels(List<String> labels) {
      this.labels = labels;
    }
    public List<Dataset> getDatasets() {
      return datasets;
    }
    public void setDatasets(List<Dataset> datasets) {
      this.datasets = datasets;
    }
  }

  public static class Dataset {
    @JsonProperty("label")
    private String label;

    @JsonProperty("data")
    private List<Double> data;

    @JsonProperty("color")
    private String color;

    // Getters and setters
    public String getLabel() {
      return label;
    }
    public void setLabel(String label) {
      this.label = label;
    }
    public List<Double> getData() {
      return data;
    }
    public void setData(List<Double> data) {
      this.data = data;
    }
    public String getColor() {
      return color;
    }
    public void setColor(String color) {
      this.color = color;
    }
  }

  public static class VisualizationConfig {
    @JsonProperty("xAxis")
    private AxisConfig xAxis;

    @JsonProperty("yAxis")
    private AxisConfig yAxis;

    @JsonProperty("legend")
    private LegendConfig legend;

    // Getters and setters
    public AxisConfig getXAxis() {
      return xAxis;
    }
    public void setXAxis(AxisConfig xAxis) {
      this.xAxis = xAxis;
    }
    public AxisConfig getYAxis() {
      return yAxis;
    }
    public void setYAxis(AxisConfig yAxis) {
      this.yAxis = yAxis;
    }
    public LegendConfig getLegend() {
      return legend;
    }
    public void setLegend(LegendConfig legend) {
      this.legend = legend;
    }
  }

  public static class AxisConfig {
    @JsonProperty("label")
    private String label;

    @JsonProperty("type")
    private String type;

    @JsonProperty("format")
    private String format;

    // Getters and setters
    public String getLabel() {
      return label;
    }
    public void setLabel(String label) {
      this.label = label;
    }
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public String getFormat() {
      return format;
    }
    public void setFormat(String format) {
      this.format = format;
    }
  }

  public static class LegendConfig {
    @JsonProperty("position")
    private String position;

    @JsonProperty("visible")
    private Boolean visible;

    // Getters and setters
    public String getPosition() {
      return position;
    }
    public void setPosition(String position) {
      this.position = position;
    }
    public Boolean getVisible() {
      return visible;
    }
    public void setVisible(Boolean visible) {
      this.visible = visible;
    }
  }

  public static class Insight {
    @JsonProperty("type")
    private String type; // anomaly, trend, correlation, recommendation

    @JsonProperty("severity")
    private String severity; // info, warning, critical

    @JsonProperty("title")
    private String title;

    @JsonProperty("description")
    private String description;

    @JsonProperty("metrics")
    private List<String> metrics;

    @JsonProperty("actions")
    private List<SuggestedAction> actions;

    // Getters and setters
    public String getType() {
      return type;
    }
    public void setType(String type) {
      this.type = type;
    }
    public String getSeverity() {
      return severity;
    }
    public void setSeverity(String severity) {
      this.severity = severity;
    }
    public String getTitle() {
      return title;
    }
    public void setTitle(String title) {
      this.title = title;
    }
    public String getDescription() {
      return description;
    }
    public void setDescription(String description) {
      this.description = description;
    }
    public List<String> getMetrics() {
      return metrics;
    }
    public void setMetrics(List<String> metrics) {
      this.metrics = metrics;
    }
    public List<SuggestedAction> getActions() {
      return actions;
    }
    public void setActions(List<SuggestedAction> actions) {
      this.actions = actions;
    }
  }

  public static class SuggestedAction {
    @JsonProperty("action")
    private String action;

    @JsonProperty("impact")
    private String impact;

    @JsonProperty("effort")
    private String effort;

    // Getters and setters
    public String getAction() {
      return action;
    }
    public void setAction(String action) {
      this.action = action;
    }
    public String getImpact() {
      return impact;
    }
    public void setImpact(String impact) {
      this.impact = impact;
    }
    public String getEffort() {
      return effort;
    }
    public void setEffort(String effort) {
      this.effort = effort;
    }
  }

  public static class ResponseMetadata {
    @JsonProperty("queryId")
    private String queryId;

    @JsonProperty("cacheHit")
    private Boolean cacheHit;

    @JsonProperty("dataFreshness")
    private String dataFreshness;

    @JsonProperty("warnings")
    private List<String> warnings;

    // Getters and setters
    public String getQueryId() {
      return queryId;
    }
    public void setQueryId(String queryId) {
      this.queryId = queryId;
    }
    public Boolean getCacheHit() {
      return cacheHit;
    }
    public void setCacheHit(Boolean cacheHit) {
      this.cacheHit = cacheHit;
    }
    public String getDataFreshness() {
      return dataFreshness;
    }
    public void setDataFreshness(String dataFreshness) {
      this.dataFreshness = dataFreshness;
    }
    public List<String> getWarnings() {
      return warnings;
    }
    public void setWarnings(List<String> warnings) {
      this.warnings = warnings;
    }
  }

  // Main class getters and setters
  public String getRequestId() {
    return requestId;
  }
  public void setRequestId(String requestId) {
    this.requestId = requestId;
  }
  public String getExecutionTime() {
    return executionTime;
  }
  public void setExecutionTime(String executionTime) {
    this.executionTime = executionTime;
  }
  public Summary getSummary() {
    return summary;
  }
  public void setSummary(Summary summary) {
    this.summary = summary;
  }
  public DataResult getData() {
    return data;
  }
  public void setData(DataResult data) {
    this.data = data;
  }
  public List<Visualization> getVisualizations() {
    return visualizations;
  }
  public void setVisualizations(List<Visualization> visualizations) {
    this.visualizations = visualizations;
  }
  public List<Insight> getInsights() {
    return insights;
  }
  public void setInsights(List<Insight> insights) {
    this.insights = insights;
  }
  public ResponseMetadata getMetadata() {
    return metadata;
  }
  public void setMetadata(ResponseMetadata metadata) {
    this.metadata = metadata;
  }
}

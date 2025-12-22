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

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Analytics dashboard request with complex filtering options.
 */
public class AnalyticsRequest {

  @JsonProperty("dashboardId")
  private String dashboardId;

  @JsonProperty("dateRange")
  private DateRange dateRange;

  @JsonProperty("filters")
  private List<Filter> filters;

  @JsonProperty("groupBy")
  private List<GroupByOption> groupBy;

  @JsonProperty("metrics")
  private List<MetricDefinition> metrics;

  @JsonProperty("sorting")
  private List<SortOption> sorting;

  @JsonProperty("pagination")
  private Pagination pagination;

  @JsonProperty("exportOptions")
  private ExportOptions exportOptions;

  // Nested types
  public static class DateRange {
    @JsonProperty("start")
    private String start;

    @JsonProperty("end")
    private String end;

    @JsonProperty("timezone")
    private String timezone;

    @JsonProperty("preset")
    private String preset; // last_7_days, last_30_days, this_month, etc.

    // Getters and setters
    public String getStart() {
      return start;
    }
    public void setStart(String start) {
      this.start = start;
    }
    public String getEnd() {
      return end;
    }
    public void setEnd(String end) {
      this.end = end;
    }
    public String getTimezone() {
      return timezone;
    }
    public void setTimezone(String timezone) {
      this.timezone = timezone;
    }
    public String getPreset() {
      return preset;
    }
    public void setPreset(String preset) {
      this.preset = preset;
    }
  }

  public static class Filter {
    @JsonProperty("field")
    private String field;

    @JsonProperty("operator")
    private String operator; // eq, ne, gt, gte, lt, lte, in, contains, between

    @JsonProperty("value")
    private Object value;

    @JsonProperty("values")
    private List<Object> values;

    @JsonProperty("logicalOperator")
    private String logicalOperator; // and, or

    @JsonProperty("nestedFilters")
    private List<Filter> nestedFilters;

    // Getters and setters
    public String getField() {
      return field;
    }
    public void setField(String field) {
      this.field = field;
    }
    public String getOperator() {
      return operator;
    }
    public void setOperator(String operator) {
      this.operator = operator;
    }
    public Object getValue() {
      return value;
    }
    public void setValue(Object value) {
      this.value = value;
    }
    public List<Object> getValues() {
      return values;
    }
    public void setValues(List<Object> values) {
      this.values = values;
    }
    public String getLogicalOperator() {
      return logicalOperator;
    }
    public void setLogicalOperator(String logicalOperator) {
      this.logicalOperator = logicalOperator;
    }
    public List<Filter> getNestedFilters() {
      return nestedFilters;
    }
    public void setNestedFilters(List<Filter> nestedFilters) {
      this.nestedFilters = nestedFilters;
    }
  }

  public static class GroupByOption {
    @JsonProperty("field")
    private String field;

    @JsonProperty("interval")
    private String interval; // hour, day, week, month, year

    @JsonProperty("alias")
    private String alias;

    // Getters and setters
    public String getField() {
      return field;
    }
    public void setField(String field) {
      this.field = field;
    }
    public String getInterval() {
      return interval;
    }
    public void setInterval(String interval) {
      this.interval = interval;
    }
    public String getAlias() {
      return alias;
    }
    public void setAlias(String alias) {
      this.alias = alias;
    }
  }

  public static class MetricDefinition {
    @JsonProperty("name")
    private String name;

    @JsonProperty("field")
    private String field;

    @JsonProperty("aggregation")
    private String aggregation; // sum, avg, count, min, max, distinct

    @JsonProperty("format")
    private String format; // number, percentage, currency

    @JsonProperty("customFormula")
    private String customFormula;

    // Getters and setters
    public String getName() {
      return name;
    }
    public void setName(String name) {
      this.name = name;
    }
    public String getField() {
      return field;
    }
    public void setField(String field) {
      this.field = field;
    }
    public String getAggregation() {
      return aggregation;
    }
    public void setAggregation(String aggregation) {
      this.aggregation = aggregation;
    }
    public String getFormat() {
      return format;
    }
    public void setFormat(String format) {
      this.format = format;
    }
    public String getCustomFormula() {
      return customFormula;
    }
    public void setCustomFormula(String customFormula) {
      this.customFormula = customFormula;
    }
  }

  public static class SortOption {
    @JsonProperty("field")
    private String field;

    @JsonProperty("direction")
    private String direction; // asc, desc

    // Getters and setters
    public String getField() {
      return field;
    }
    public void setField(String field) {
      this.field = field;
    }
    public String getDirection() {
      return direction;
    }
    public void setDirection(String direction) {
      this.direction = direction;
    }
  }

  public static class Pagination {
    @JsonProperty("page")
    private Integer page;

    @JsonProperty("pageSize")
    private Integer pageSize;

    @JsonProperty("offset")
    private Integer offset;

    // Getters and setters
    public Integer getPage() {
      return page;
    }
    public void setPage(Integer page) {
      this.page = page;
    }
    public Integer getPageSize() {
      return pageSize;
    }
    public void setPageSize(Integer pageSize) {
      this.pageSize = pageSize;
    }
    public Integer getOffset() {
      return offset;
    }
    public void setOffset(Integer offset) {
      this.offset = offset;
    }
  }

  public static class ExportOptions {
    @JsonProperty("format")
    private String format; // csv, json, excel, pdf

    @JsonProperty("includeHeaders")
    private Boolean includeHeaders;

    @JsonProperty("filename")
    private String filename;

    @JsonProperty("compression")
    private String compression; // none, gzip, zip

    // Getters and setters
    public String getFormat() {
      return format;
    }
    public void setFormat(String format) {
      this.format = format;
    }
    public Boolean getIncludeHeaders() {
      return includeHeaders;
    }
    public void setIncludeHeaders(Boolean includeHeaders) {
      this.includeHeaders = includeHeaders;
    }
    public String getFilename() {
      return filename;
    }
    public void setFilename(String filename) {
      this.filename = filename;
    }
    public String getCompression() {
      return compression;
    }
    public void setCompression(String compression) {
      this.compression = compression;
    }
  }

  // Main class getters and setters
  public String getDashboardId() {
    return dashboardId;
  }
  public void setDashboardId(String dashboardId) {
    this.dashboardId = dashboardId;
  }
  public DateRange getDateRange() {
    return dateRange;
  }
  public void setDateRange(DateRange dateRange) {
    this.dateRange = dateRange;
  }
  public List<Filter> getFilters() {
    return filters;
  }
  public void setFilters(List<Filter> filters) {
    this.filters = filters;
  }
  public List<GroupByOption> getGroupBy() {
    return groupBy;
  }
  public void setGroupBy(List<GroupByOption> groupBy) {
    this.groupBy = groupBy;
  }
  public List<MetricDefinition> getMetrics() {
    return metrics;
  }
  public void setMetrics(List<MetricDefinition> metrics) {
    this.metrics = metrics;
  }
  public List<SortOption> getSorting() {
    return sorting;
  }
  public void setSorting(List<SortOption> sorting) {
    this.sorting = sorting;
  }
  public Pagination getPagination() {
    return pagination;
  }
  public void setPagination(Pagination pagination) {
    this.pagination = pagination;
  }
  public ExportOptions getExportOptions() {
    return exportOptions;
  }
  public void setExportOptions(ExportOptions exportOptions) {
    this.exportOptions = exportOptions;
  }
}

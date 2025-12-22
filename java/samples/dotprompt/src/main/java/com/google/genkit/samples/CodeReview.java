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

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * Code review analysis output schema.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CodeReview {

    @JsonProperty("language")
    private String language;

    @JsonProperty("summary")
    private String summary;

    @JsonProperty("complexity")
    private Complexity complexity;

    @JsonProperty("issues")
    private List<Issue> issues;

    @JsonProperty("improvements")
    private List<Improvement> improvements;

    @JsonProperty("metrics")
    private Metrics metrics;

    // Getters and setters
    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public Complexity getComplexity() {
        return complexity;
    }

    public void setComplexity(Complexity complexity) {
        this.complexity = complexity;
    }

    public List<Issue> getIssues() {
        return issues;
    }

    public void setIssues(List<Issue> issues) {
        this.issues = issues;
    }

    public List<Improvement> getImprovements() {
        return improvements;
    }

    public void setImprovements(List<Improvement> improvements) {
        this.improvements = improvements;
    }

    public Metrics getMetrics() {
        return metrics;
    }

    public void setMetrics(Metrics metrics) {
        this.metrics = metrics;
    }

    /**
     * Complexity assessment.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Complexity {
        @JsonProperty("level")
        private String level;

        @JsonProperty("score")
        private Integer score;

        @JsonProperty("explanation")
        private String explanation;

        public String getLevel() {
            return level;
        }

        public void setLevel(String level) {
            this.level = level;
        }

        public Integer getScore() {
            return score;
        }

        public void setScore(Integer score) {
            this.score = score;
        }

        public String getExplanation() {
            return explanation;
        }

        public void setExplanation(String explanation) {
            this.explanation = explanation;
        }
    }

    /**
     * Code issue.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Issue {
        @JsonProperty("severity")
        private String severity;

        @JsonProperty("line")
        private Integer line;

        @JsonProperty("description")
        private String description;

        @JsonProperty("suggestion")
        private String suggestion;

        public String getSeverity() {
            return severity;
        }

        public void setSeverity(String severity) {
            this.severity = severity;
        }

        public Integer getLine() {
            return line;
        }

        public void setLine(Integer line) {
            this.line = line;
        }

        public String getDescription() {
            return description;
        }

        public void setDescription(String description) {
            this.description = description;
        }

        public String getSuggestion() {
            return suggestion;
        }

        public void setSuggestion(String suggestion) {
            this.suggestion = suggestion;
        }
    }

    /**
     * Code improvement suggestion.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Improvement {
        @JsonProperty("category")
        private String category;

        @JsonProperty("description")
        private String description;

        @JsonProperty("example")
        private String example;

        public String getCategory() {
            return category;
        }

        public void setCategory(String category) {
            this.category = category;
        }

        public String getDescription() {
            return description;
        }

        public void setDescription(String description) {
            this.description = description;
        }

        public String getExample() {
            return example;
        }

        public void setExample(String example) {
            this.example = example;
        }
    }

    /**
     * Code metrics.
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Metrics {
        @JsonProperty("linesOfCode")
        private Integer linesOfCode;

        @JsonProperty("functions")
        private Integer functions;

        @JsonProperty("classes")
        private Integer classes;

        @JsonProperty("comments")
        private Integer comments;

        public Integer getLinesOfCode() {
            return linesOfCode;
        }

        public void setLinesOfCode(Integer linesOfCode) {
            this.linesOfCode = linesOfCode;
        }

        public Integer getFunctions() {
            return functions;
        }

        public void setFunctions(Integer functions) {
            this.functions = functions;
        }

        public Integer getClasses() {
            return classes;
        }

        public void setClasses(Integer classes) {
            this.classes = classes;
        }

        public Integer getComments() {
            return comments;
        }

        public void setComments(Integer comments) {
            this.comments = comments;
        }
    }
}

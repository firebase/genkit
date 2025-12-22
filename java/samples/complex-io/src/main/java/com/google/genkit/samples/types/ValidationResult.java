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
 * Validation result with errors and warnings.
 */
public class ValidationResult {

  @JsonProperty("valid")
  private Boolean valid;

  @JsonProperty("errors")
  private List<ValidationError> errors;

  @JsonProperty("warnings")
  private List<ValidationWarning> warnings;

  @JsonProperty("errorCount")
  private Integer errorCount;

  @JsonProperty("warningCount")
  private Integer warningCount;

  // Nested types
  public static class ValidationError {
    @JsonProperty("field")
    private String field;

    @JsonProperty("message")
    private String message;

    @JsonProperty("severity")
    private String severity;

    @JsonProperty("code")
    private String code;

    // Getters and setters
    public String getField() {
      return field;
    }
    public void setField(String field) {
      this.field = field;
    }
    public String getMessage() {
      return message;
    }
    public void setMessage(String message) {
      this.message = message;
    }
    public String getSeverity() {
      return severity;
    }
    public void setSeverity(String severity) {
      this.severity = severity;
    }
    public String getCode() {
      return code;
    }
    public void setCode(String code) {
      this.code = code;
    }
  }

  public static class ValidationWarning {
    @JsonProperty("field")
    private String field;

    @JsonProperty("message")
    private String message;

    // Getters and setters
    public String getField() {
      return field;
    }
    public void setField(String field) {
      this.field = field;
    }
    public String getMessage() {
      return message;
    }
    public void setMessage(String message) {
      this.message = message;
    }
  }

  // Main class getters and setters
  public Boolean getValid() {
    return valid;
  }
  public void setValid(Boolean valid) {
    this.valid = valid;
  }
  public List<ValidationError> getErrors() {
    return errors;
  }
  public void setErrors(List<ValidationError> errors) {
    this.errors = errors;
  }
  public List<ValidationWarning> getWarnings() {
    return warnings;
  }
  public void setWarnings(List<ValidationWarning> warnings) {
    this.warnings = warnings;
  }
  public Integer getErrorCount() {
    return errorCount;
  }
  public void setErrorCount(Integer errorCount) {
    this.errorCount = errorCount;
  }
  public Integer getWarningCount() {
    return warningCount;
  }
  public void setWarningCount(Integer warningCount) {
    this.warningCount = warningCount;
  }
}

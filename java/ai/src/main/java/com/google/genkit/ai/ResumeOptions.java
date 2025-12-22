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

package com.google.genkit.ai;

import java.util.ArrayList;
import java.util.List;

/**
 * Options for resuming after an interrupt.
 *
 * <p>
 * When generation is interrupted by a tool, you can resume by providing
 * responses to the interrupted tool requests or by restarting them with new
 * inputs.
 *
 * <p>
 * Example usage:
 *
 * <pre>{@code
 * // Respond to an interrupt
 * ResumeOptions resume = ResumeOptions.builder().respond(interrupt.respond("user confirmed")).build();
 *
 * // Restart an interrupt with new input
 * ResumeOptions resume = ResumeOptions.builder().restart(interrupt.restart(null, newInput)).build();
 * }</pre>
 */
public class ResumeOptions {

  private List<ToolResponse> respond;
  private List<ToolRequest> restart;

  /** Default constructor. */
  public ResumeOptions() {
  }

  /**
   * Gets the tool responses for interrupted requests.
   *
   * @return the tool responses
   */
  public List<ToolResponse> getRespond() {
    return respond;
  }

  /**
   * Sets the tool responses for interrupted requests.
   *
   * @param respond
   *            the tool responses
   */
  public void setRespond(List<ToolResponse> respond) {
    this.respond = respond;
  }

  /**
   * Gets the tool requests to restart.
   *
   * @return the tool requests to restart
   */
  public List<ToolRequest> getRestart() {
    return restart;
  }

  /**
   * Sets the tool requests to restart.
   *
   * @param restart
   *            the tool requests to restart
   */
  public void setRestart(List<ToolRequest> restart) {
    this.restart = restart;
  }

  /**
   * Creates a new builder.
   *
   * @return a new builder
   */
  public static Builder builder() {
    return new Builder();
  }

  /** Builder for ResumeOptions. */
  public static class Builder {
    private List<ToolResponse> respond;
    private List<ToolRequest> restart;

    /**
     * Adds a tool response.
     *
     * @param response
     *            the tool response
     * @return this builder
     */
    public Builder respond(ToolResponse response) {
      if (this.respond == null) {
        this.respond = new ArrayList<>();
      }
      this.respond.add(response);
      return this;
    }

    /**
     * Sets all tool responses.
     *
     * @param responses
     *            the tool responses
     * @return this builder
     */
    public Builder respond(List<ToolResponse> responses) {
      this.respond = responses;
      return this;
    }

    /**
     * Adds a tool request to restart.
     *
     * @param request
     *            the tool request
     * @return this builder
     */
    public Builder restart(ToolRequest request) {
      if (this.restart == null) {
        this.restart = new ArrayList<>();
      }
      this.restart.add(request);
      return this;
    }

    /**
     * Sets all tool requests to restart.
     *
     * @param requests
     *            the tool requests
     * @return this builder
     */
    public Builder restart(List<ToolRequest> requests) {
      this.restart = requests;
      return this;
    }

    /**
     * Builds the ResumeOptions.
     *
     * @return the built options
     */
    public ResumeOptions build() {
      ResumeOptions options = new ResumeOptions();
      options.setRespond(respond);
      options.setRestart(restart);
      return options;
    }
  }
}

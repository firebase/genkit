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

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * FinishReason indicates why the model stopped generating.
 */
public enum FinishReason {

  @JsonProperty("stop")
  STOP,

  @JsonProperty("length")
  LENGTH,

  @JsonProperty("blocked")
  BLOCKED,

  @JsonProperty("interrupted")
  INTERRUPTED,

  @JsonProperty("other")
  OTHER,

  @JsonProperty("unknown")
  UNKNOWN
}

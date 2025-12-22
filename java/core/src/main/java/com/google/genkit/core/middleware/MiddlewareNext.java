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

package com.google.genkit.core.middleware;

import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

/**
 * MiddlewareNext represents the next function in the middleware chain. It is
 * used by middleware to pass control to the next middleware or the actual
 * action.
 *
 * @param <I>
 *            The input type
 * @param <O>
 *            The output type
 */
@FunctionalInterface
public interface MiddlewareNext<I, O> {

  /**
   * Calls the next middleware in the chain or the actual action.
   *
   * @param request
   *            the input request (may be modified by the middleware)
   * @param context
   *            the action context (may be modified by the middleware)
   * @return the output response
   * @throws GenkitException
   *             if processing fails
   */
  O apply(I request, ActionContext context) throws GenkitException;
}

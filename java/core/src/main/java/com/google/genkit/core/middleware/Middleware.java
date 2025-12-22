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
 * Middleware is a function that wraps action execution, allowing pre-processing
 * and post-processing of requests and responses.
 *
 * <p>
 * Middleware functions receive the request, action context, and a "next"
 * function to call the next middleware in the chain (or the actual action if at
 * the end of the chain).
 *
 * <p>
 * Example usage:
 *
 * <pre>
 * {@code
 * Middleware<String, String> loggingMiddleware = (request, context, next) -> {
 * 	System.out.println("Before: " + request);
 * 	String result = next.apply(request, context);
 * 	System.out.println("After: " + result);
 * 	return result;
 * };
 * }
 * </pre>
 *
 * @param <I>
 *            The input type
 * @param <O>
 *            The output type
 */
@FunctionalInterface
public interface Middleware<I, O> {

  /**
   * Processes the request through this middleware.
   *
   * @param request
   *            the input request
   * @param context
   *            the action context
   * @param next
   *            the next function in the middleware chain
   * @return the output response
   * @throws GenkitException
   *             if processing fails
   */
  O handle(I request, ActionContext context, MiddlewareNext<I, O> next) throws GenkitException;
}

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

/**
 * Middleware support for Genkit Java.
 *
 * <p>
 * This package provides a middleware pattern implementation for wrapping action
 * execution with pre-processing and post-processing logic. Middleware can be
 * used for:
 * <ul>
 * <li>Logging and monitoring</li>
 * <li>Request/response transformation</li>
 * <li>Caching</li>
 * <li>Rate limiting</li>
 * <li>Retry logic</li>
 * <li>Validation</li>
 * <li>Error handling</li>
 * </ul>
 *
 * <p>
 * Example usage:
 *
 * <pre>
 * {@code
 * // Create a middleware chain
 * MiddlewareChain<String, String> chain = new MiddlewareChain<>();
 * chain.use(CommonMiddleware.logging("myAction"));
 * chain.use(CommonMiddleware.retry(3, 100));
 *
 * // Execute with middleware
 * String result = chain.execute(input, context, (ctx, req) -> {
 * 	// Actual action logic
 * 	return "Hello, " + req;
 * });
 * }
 * </pre>
 *
 * @see com.google.genkit.core.middleware.Middleware
 * @see com.google.genkit.core.middleware.MiddlewareChain
 * @see com.google.genkit.core.middleware.CommonMiddleware
 */
package com.google.genkit.core.middleware;

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

package com.google.genkit.ai.session;

import java.util.concurrent.CompletableFuture;

/**
 * SessionStore is an interface for persisting session data.
 * 
 * <p>
 * Implementations can provide different storage backends such as:
 * <ul>
 * <li>In-memory storage (for development/testing)</li>
 * <li>Database storage (for production)</li>
 * <li>Redis or other distributed cache</li>
 * <li>File-based storage</li>
 * </ul>
 *
 * @param <S>
 *            the type of the custom session state
 */
public interface SessionStore<S> {

  /**
   * Retrieves a session by its ID.
   *
   * @param sessionId
   *            the session ID
   * @return a CompletableFuture containing the session data, or null if not found
   */
  CompletableFuture<SessionData<S>> get(String sessionId);

  /**
   * Saves session data.
   *
   * @param sessionId
   *            the session ID
   * @param data
   *            the session data to save
   * @return a CompletableFuture that completes when the save is done
   */
  CompletableFuture<Void> save(String sessionId, SessionData<S> data);

  /**
   * Deletes a session by its ID.
   *
   * @param sessionId
   *            the session ID
   * @return a CompletableFuture that completes when the deletion is done
   */
  default CompletableFuture<Void> delete(String sessionId) {
    return CompletableFuture.completedFuture(null);
  }

  /**
   * Checks if a session exists.
   *
   * @param sessionId
   *            the session ID
   * @return a CompletableFuture containing true if the session exists
   */
  default CompletableFuture<Boolean> exists(String sessionId) {
    return get(sessionId).thenApply(data -> data != null);
  }
}

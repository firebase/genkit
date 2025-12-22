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

import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

/**
 * InMemorySessionStore is a simple in-memory implementation of SessionStore.
 * 
 * <p>
 * This implementation is suitable for:
 * <ul>
 * <li>Development and testing</li>
 * <li>Single-instance deployments</li>
 * <li>Prototyping</li>
 * </ul>
 * 
 * <p>
 * <b>Note:</b> Sessions are lost when the application restarts. For production
 * use cases requiring persistence, implement a database-backed SessionStore.
 *
 * @param <S>
 *            the type of the custom session state
 */
public class InMemorySessionStore<S> implements SessionStore<S> {

  private final Map<String, SessionData<S>> data = new ConcurrentHashMap<>();

  /**
   * Creates a new InMemorySessionStore.
   */
  public InMemorySessionStore() {
  }

  @Override
  public CompletableFuture<SessionData<S>> get(String sessionId) {
    return CompletableFuture.completedFuture(data.get(sessionId));
  }

  @Override
  public CompletableFuture<Void> save(String sessionId, SessionData<S> sessionData) {
    data.put(sessionId, sessionData);
    return CompletableFuture.completedFuture(null);
  }

  @Override
  public CompletableFuture<Void> delete(String sessionId) {
    data.remove(sessionId);
    return CompletableFuture.completedFuture(null);
  }

  @Override
  public CompletableFuture<Boolean> exists(String sessionId) {
    return CompletableFuture.completedFuture(data.containsKey(sessionId));
  }

  /**
   * Returns the number of sessions currently stored.
   *
   * @return the session count
   */
  public int size() {
    return data.size();
  }

  /**
   * Clears all sessions from the store.
   */
  public void clear() {
    data.clear();
  }
}

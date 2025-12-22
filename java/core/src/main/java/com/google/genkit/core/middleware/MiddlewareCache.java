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

/**
 * MiddlewareCache is a simple cache interface for use with caching middleware.
 *
 * @param <V>
 *            the value type
 */
public interface MiddlewareCache<V> {

  /**
   * Gets a value from the cache.
   *
   * @param key
   *            the cache key
   * @return the cached value, or null if not found
   */
  V get(String key);

  /**
   * Puts a value in the cache.
   *
   * @param key
   *            the cache key
   * @param value
   *            the value to cache
   */
  void put(String key, V value);

  /**
   * Removes a value from the cache.
   *
   * @param key
   *            the cache key
   */
  void remove(String key);

  /**
   * Clears all values from the cache.
   */
  void clear();
}

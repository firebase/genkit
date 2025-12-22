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

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * SimpleCache is a thread-safe in-memory cache implementation for use with
 * caching middleware.
 *
 * @param <V>
 *            the value type
 */
public class SimpleCache<V> implements MiddlewareCache<V> {

  private final Map<String, CacheEntry<V>> cache;
  private final long ttlMs;

  /**
   * Creates a SimpleCache with no TTL (entries never expire).
   */
  public SimpleCache() {
    this(0);
  }

  /**
   * Creates a SimpleCache with the specified TTL.
   *
   * @param ttlMs
   *            time-to-live in milliseconds (0 for no expiration)
   */
  public SimpleCache(long ttlMs) {
    this.cache = new ConcurrentHashMap<>();
    this.ttlMs = ttlMs;
  }

  @Override
  public V get(String key) {
    CacheEntry<V> entry = cache.get(key);
    if (entry == null) {
      return null;
    }
    if (ttlMs > 0 && System.currentTimeMillis() - entry.timestamp > ttlMs) {
      cache.remove(key);
      return null;
    }
    return entry.value;
  }

  @Override
  public void put(String key, V value) {
    cache.put(key, new CacheEntry<>(value, System.currentTimeMillis()));
  }

  @Override
  public void remove(String key) {
    cache.remove(key);
  }

  @Override
  public void clear() {
    cache.clear();
  }

  /**
   * Returns the number of entries in the cache.
   *
   * @return the cache size
   */
  public int size() {
    return cache.size();
  }

  private static class CacheEntry<V> {

    final V value;
    final long timestamp;

    CacheEntry(V value, long timestamp) {
      this.value = value;
      this.timestamp = timestamp;
    }
  }
}

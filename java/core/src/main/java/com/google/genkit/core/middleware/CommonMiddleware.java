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

import java.time.Duration;
import java.time.Instant;
import java.util.function.BiConsumer;
import java.util.function.BiPredicate;
import java.util.function.Consumer;
import java.util.function.Function;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

/**
 * CommonMiddleware provides factory methods for creating commonly-used
 * middleware functions.
 */
public final class CommonMiddleware {

  private static final Logger logger = LoggerFactory.getLogger(CommonMiddleware.class);

  private CommonMiddleware() {
    // Utility class
  }

  /**
   * Creates a logging middleware that logs requests and responses.
   *
   * @param name
   *            the name to use in log messages
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a logging middleware
   */
  public static <I, O> Middleware<I, O> logging(String name) {
    return (request, context, next) -> {
      logger.info("[{}] Request: {}", name, request);
      Instant start = Instant.now();
      try {
        O result = next.apply(request, context);
        Duration duration = Duration.between(start, Instant.now());
        logger.info("[{}] Response ({}ms): {}", name, duration.toMillis(), result);
        return result;
      } catch (GenkitException e) {
        Duration duration = Duration.between(start, Instant.now());
        logger.error("[{}] Error ({}ms): {}", name, duration.toMillis(), e.getMessage());
        throw e;
      }
    };
  }

  /**
   * Creates a logging middleware with a custom logger.
   *
   * @param name
   *            the name to use in log messages
   * @param customLogger
   *            the logger to use
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a logging middleware
   */
  public static <I, O> Middleware<I, O> logging(String name, Logger customLogger) {
    return (request, context, next) -> {
      customLogger.info("[{}] Request: {}", name, request);
      Instant start = Instant.now();
      try {
        O result = next.apply(request, context);
        Duration duration = Duration.between(start, Instant.now());
        customLogger.info("[{}] Response ({}ms): {}", name, duration.toMillis(), result);
        return result;
      } catch (GenkitException e) {
        Duration duration = Duration.between(start, Instant.now());
        customLogger.error("[{}] Error ({}ms): {}", name, duration.toMillis(), e.getMessage());
        throw e;
      }
    };
  }

  /**
   * Creates a timing middleware that measures execution time.
   *
   * @param callback
   *            callback to receive timing information (duration in milliseconds)
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a timing middleware
   */
  public static <I, O> Middleware<I, O> timing(Consumer<Long> callback) {
    return (request, context, next) -> {
      Instant start = Instant.now();
      try {
        return next.apply(request, context);
      } finally {
        Duration duration = Duration.between(start, Instant.now());
        callback.accept(duration.toMillis());
      }
    };
  }

  /**
   * Creates a retry middleware with exponential backoff.
   *
   * @param maxRetries
   *            maximum number of retry attempts
   * @param initialDelayMs
   *            initial delay between retries in milliseconds
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a retry middleware
   */
  public static <I, O> Middleware<I, O> retry(int maxRetries, long initialDelayMs) {
    return retry(maxRetries, initialDelayMs, e -> true);
  }

  /**
   * Creates a retry middleware with exponential backoff and custom retry
   * predicate.
   *
   * @param maxRetries
   *            maximum number of retry attempts
   * @param initialDelayMs
   *            initial delay between retries in milliseconds
   * @param shouldRetry
   *            predicate to determine if an exception should trigger a retry
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a retry middleware
   */
  public static <I, O> Middleware<I, O> retry(int maxRetries, long initialDelayMs,
      Function<GenkitException, Boolean> shouldRetry) {
    return (request, context, next) -> {
      int attempt = 0;
      GenkitException lastException = null;
      long delay = initialDelayMs;

      while (attempt <= maxRetries) {
        try {
          return next.apply(request, context);
        } catch (GenkitException e) {
          lastException = e;
          if (attempt >= maxRetries || !shouldRetry.apply(e)) {
            throw e;
          }
          attempt++;
          logger.warn("Retry attempt {} after error: {}", attempt, e.getMessage());
          try {
            Thread.sleep(delay);
          } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            throw new GenkitException("Retry interrupted", ie);
          }
          delay *= 2; // Exponential backoff
        }
      }
      throw lastException;
    };
  }

  /**
   * Creates a validation middleware that validates the request before processing.
   *
   * @param validator
   *            the validation function (throws GenkitException on invalid input)
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a validation middleware
   */
  public static <I, O> Middleware<I, O> validate(Consumer<I> validator) {
    return (request, context, next) -> {
      validator.accept(request);
      return next.apply(request, context);
    };
  }

  /**
   * Creates a transformation middleware that transforms the request before
   * processing.
   *
   * @param transformer
   *            the transformation function
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a transformation middleware
   */
  public static <I, O> Middleware<I, O> transformRequest(Function<I, I> transformer) {
    return (request, context, next) -> {
      I transformed = transformer.apply(request);
      return next.apply(transformed, context);
    };
  }

  /**
   * Creates a transformation middleware that transforms the response after
   * processing.
   *
   * @param transformer
   *            the transformation function
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a transformation middleware
   */
  public static <I, O> Middleware<I, O> transformResponse(Function<O, O> transformer) {
    return (request, context, next) -> {
      O result = next.apply(request, context);
      return transformer.apply(result);
    };
  }

  /**
   * Creates a caching middleware that caches results based on a key.
   *
   * @param cache
   *            the cache implementation
   * @param keyExtractor
   *            function to extract cache key from request
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a caching middleware
   */
  public static <I, O> Middleware<I, O> cache(MiddlewareCache<O> cache, Function<I, String> keyExtractor) {
    return (request, context, next) -> {
      String key = keyExtractor.apply(request);
      O cached = cache.get(key);
      if (cached != null) {
        logger.debug("Cache hit for key: {}", key);
        return cached;
      }
      O result = next.apply(request, context);
      cache.put(key, result);
      return result;
    };
  }

  /**
   * Creates an error handling middleware that catches and transforms exceptions.
   *
   * @param errorHandler
   *            the error handler function
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return an error handling middleware
   */
  public static <I, O> Middleware<I, O> errorHandler(Function<GenkitException, O> errorHandler) {
    return (request, context, next) -> {
      try {
        return next.apply(request, context);
      } catch (GenkitException e) {
        return errorHandler.apply(e);
      }
    };
  }

  /**
   * Creates a conditional middleware that only applies if the predicate is true.
   *
   * @param predicate
   *            the condition to check
   * @param middleware
   *            the middleware to apply if condition is true
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a conditional middleware
   */
  public static <I, O> Middleware<I, O> conditional(BiPredicate<I, ActionContext> predicate,
      Middleware<I, O> middleware) {
    return (request, context, next) -> {
      if (predicate.test(request, context)) {
        return middleware.handle(request, context, next);
      }
      return next.apply(request, context);
    };
  }

  /**
   * Creates a before/after middleware that runs callbacks before and after
   * execution.
   *
   * @param before
   *            callback to run before execution
   * @param after
   *            callback to run after execution
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a before/after middleware
   */
  public static <I, O> Middleware<I, O> beforeAfter(BiConsumer<I, ActionContext> before,
      BiConsumer<O, ActionContext> after) {
    return (request, context, next) -> {
      if (before != null) {
        before.accept(request, context);
      }
      O result = next.apply(request, context);
      if (after != null) {
        after.accept(result, context);
      }
      return result;
    };
  }

  /**
   * Creates a rate limiting middleware (simple token bucket implementation).
   *
   * @param maxRequests
   *            maximum requests allowed in the time window
   * @param windowMs
   *            time window in milliseconds
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a rate limiting middleware
   */
  public static <I, O> Middleware<I, O> rateLimit(int maxRequests, long windowMs) {
    return new RateLimitMiddleware<>(maxRequests, windowMs);
  }

  /**
   * Creates a timeout middleware that throws an exception if execution takes too
   * long.
   *
   * @param timeoutMs
   *            timeout in milliseconds
   * @param <I>
   *            input type
   * @param <O>
   *            output type
   * @return a timeout middleware
   */
  public static <I, O> Middleware<I, O> timeout(long timeoutMs) {
    return (request, context, next) -> {
      // Note: This is a simple implementation. For true timeout support,
      // you would need to use CompletableFuture or similar async patterns.
      Instant start = Instant.now();
      O result = next.apply(request, context);
      Duration duration = Duration.between(start, Instant.now());
      if (duration.toMillis() > timeoutMs) {
        logger.warn("Execution exceeded timeout: {}ms > {}ms", duration.toMillis(), timeoutMs);
      }
      return result;
    };
  }

  /**
   * Simple rate limiting middleware implementation.
   */
  private static class RateLimitMiddleware<I, O> implements Middleware<I, O> {

    private final int maxRequests;
    private final long windowMs;
    private int requestCount;
    private long windowStart;

    RateLimitMiddleware(int maxRequests, long windowMs) {
      this.maxRequests = maxRequests;
      this.windowMs = windowMs;
      this.requestCount = 0;
      this.windowStart = System.currentTimeMillis();
    }

    @Override
    public synchronized O handle(I request, ActionContext context, MiddlewareNext<I, O> next)
        throws GenkitException {
      long now = System.currentTimeMillis();

      // Reset window if expired
      if (now - windowStart >= windowMs) {
        windowStart = now;
        requestCount = 0;
      }

      // Check rate limit
      if (requestCount >= maxRequests) {
        throw new GenkitException("Rate limit exceeded: " + maxRequests + " requests per " + windowMs + "ms");
      }

      requestCount++;
      return next.apply(request, context);
    }
  }
}

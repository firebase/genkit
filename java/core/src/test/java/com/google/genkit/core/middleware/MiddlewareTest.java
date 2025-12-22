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

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.google.genkit.core.ActionContext;
import com.google.genkit.core.DefaultRegistry;
import com.google.genkit.core.GenkitException;

/**
 * Tests for the Middleware classes.
 */
class MiddlewareTest {

  private ActionContext context;

  @BeforeEach
  void setUp() {
    context = new ActionContext(new DefaultRegistry());
  }

  @Test
  void testSimpleMiddleware() {
    Middleware<String, String> middleware = (request, ctx, next) -> {
      String modified = request.toUpperCase();
      return next.apply(modified, ctx);
    };

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(middleware);

    String result = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("Result: HELLO", result);
  }

  @Test
  void testMiddlewareChainOrder() {
    List<String> order = new ArrayList<>();

    Middleware<String, String> first = (request, ctx, next) -> {
      order.add("first-before");
      String result = next.apply(request + "-first", ctx);
      order.add("first-after");
      return result;
    };

    Middleware<String, String> second = (request, ctx, next) -> {
      order.add("second-before");
      String result = next.apply(request + "-second", ctx);
      order.add("second-after");
      return result;
    };

    MiddlewareChain<String, String> chain = MiddlewareChain.of(first, second);

    String result = chain.execute("input", context, (ctx, req) -> {
      order.add("action");
      return req;
    });

    assertEquals("input-first-second", result);
    assertEquals(List.of("first-before", "second-before", "action", "second-after", "first-after"), order);
  }

  @Test
  void testEmptyMiddlewareChain() {
    MiddlewareChain<String, String> chain = new MiddlewareChain<>();

    String result = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("Result: hello", result);
  }

  @Test
  void testMiddlewareModifiesResponse() {
    Middleware<String, String> middleware = (request, ctx, next) -> {
      String result = next.apply(request, ctx);
      return result.toUpperCase();
    };

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(middleware);

    String result = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("RESULT: HELLO", result);
  }

  @Test
  void testLoggingMiddleware() {
    Middleware<String, String> loggingMiddleware = CommonMiddleware.logging("test");

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(loggingMiddleware);

    String result = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("Result: hello", result);
  }

  @Test
  void testRetryMiddleware() {
    AtomicInteger attempts = new AtomicInteger(0);

    Middleware<String, String> retryMiddleware = CommonMiddleware.retry(3, 10);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(retryMiddleware);

    String result = chain.execute("hello", context, (ctx, req) -> {
      int attempt = attempts.incrementAndGet();
      if (attempt < 3) {
        throw new GenkitException("Simulated failure");
      }
      return "Success after " + attempt + " attempts";
    });

    assertEquals("Success after 3 attempts", result);
    assertEquals(3, attempts.get());
  }

  @Test
  void testRetryMiddlewareMaxRetriesExceeded() {
    AtomicInteger attempts = new AtomicInteger(0);

    Middleware<String, String> retryMiddleware = CommonMiddleware.retry(2, 10);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(retryMiddleware);

    GenkitException exception = assertThrows(GenkitException.class, () -> {
      chain.execute("hello", context, (ctx, req) -> {
        attempts.incrementAndGet();
        throw new GenkitException("Simulated failure");
      });
    });

    assertTrue(exception.getMessage().contains("Simulated failure"));
    assertEquals(3, attempts.get()); // Initial + 2 retries
  }

  @Test
  void testValidationMiddleware() {
    Middleware<String, String> validationMiddleware = CommonMiddleware.validate(request -> {
      if (request == null || request.isEmpty()) {
        throw new GenkitException("Request cannot be empty");
      }
    });

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(validationMiddleware);

    // Valid request
    String result = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("Result: hello", result);

    // Invalid request
    GenkitException exception = assertThrows(GenkitException.class, () -> {
      chain.execute("", context, (ctx, req) -> "Result: " + req);
    });
    assertTrue(exception.getMessage().contains("empty"));
  }

  @Test
  void testTransformRequestMiddleware() {
    Middleware<String, String> transformMiddleware = CommonMiddleware.transformRequest(String::trim);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(transformMiddleware);

    String result = chain.execute("  hello  ", context, (ctx, req) -> "Result: " + req);
    assertEquals("Result: hello", result);
  }

  @Test
  void testTransformResponseMiddleware() {
    Middleware<String, String> transformMiddleware = CommonMiddleware.transformResponse(String::toUpperCase);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(transformMiddleware);

    String result = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("RESULT: HELLO", result);
  }

  @Test
  void testTimingMiddleware() {
    List<Long> timings = new ArrayList<>();
    Middleware<String, String> timingMiddleware = CommonMiddleware.timing(timings::add);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(timingMiddleware);

    String result = chain.execute("hello", context, (ctx, req) -> {
      try {
        Thread.sleep(50);
      } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
      }
      return "Result: " + req;
    });

    assertEquals("Result: hello", result);
    assertEquals(1, timings.size());
    assertTrue(timings.get(0) >= 50);
  }

  @Test
  void testCacheMiddleware() {
    SimpleCache<String> cache = new SimpleCache<>();
    AtomicInteger actionCalls = new AtomicInteger(0);

    Middleware<String, String> cacheMiddleware = CommonMiddleware.cache(cache, request -> request);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(cacheMiddleware);

    // First call - should execute action
    String result1 = chain.execute("hello", context, (ctx, req) -> {
      actionCalls.incrementAndGet();
      return "Result: " + req;
    });

    // Second call - should use cache
    String result2 = chain.execute("hello", context, (ctx, req) -> {
      actionCalls.incrementAndGet();
      return "Result: " + req;
    });

    assertEquals("Result: hello", result1);
    assertEquals("Result: hello", result2);
    assertEquals(1, actionCalls.get()); // Action should only be called once
  }

  @Test
  void testConditionalMiddleware() {
    Middleware<String, String> upperCaseMiddleware = (request, ctx, next) -> {
      return next.apply(request.toUpperCase(), ctx);
    };

    Middleware<String, String> conditionalMiddleware = CommonMiddleware
        .conditional((request, ctx) -> request.startsWith("transform:"), upperCaseMiddleware);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(conditionalMiddleware);

    // Should apply middleware
    String result1 = chain.execute("transform:hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("Result: TRANSFORM:HELLO", result1);

    // Should skip middleware
    String result2 = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    assertEquals("Result: hello", result2);
  }

  @Test
  void testErrorHandlerMiddleware() {
    Middleware<String, String> errorHandler = CommonMiddleware
        .errorHandler(e -> "Error handled: " + e.getMessage());

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(errorHandler);

    String result = chain.execute("hello", context, (ctx, req) -> {
      throw new GenkitException("Something went wrong");
    });

    assertEquals("Error handled: Something went wrong", result);
  }

  @Test
  void testRateLimitMiddleware() {
    Middleware<String, String> rateLimitMiddleware = CommonMiddleware.rateLimit(2, 1000);

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(rateLimitMiddleware);

    // First two calls should succeed
    String result1 = chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    String result2 = chain.execute("hello", context, (ctx, req) -> "Result: " + req);

    assertEquals("Result: hello", result1);
    assertEquals("Result: hello", result2);

    // Third call should fail
    GenkitException exception = assertThrows(GenkitException.class, () -> {
      chain.execute("hello", context, (ctx, req) -> "Result: " + req);
    });
    assertTrue(exception.getMessage().contains("Rate limit exceeded"));
  }

  @Test
  void testBeforeAfterMiddleware() {
    List<String> events = new ArrayList<>();

    Middleware<String, String> beforeAfterMiddleware = CommonMiddleware.beforeAfter(
        (request, ctx) -> events.add("before: " + request),
        (response, ctx) -> events.add("after: " + response));

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(beforeAfterMiddleware);

    String result = chain.execute("hello", context, (ctx, req) -> "Result: " + req);

    assertEquals("Result: hello", result);
    assertEquals(List.of("before: hello", "after: Result: hello"), events);
  }

  @Test
  void testMiddlewareChainCopy() {
    Middleware<String, String> middleware = (request, ctx, next) -> next.apply(request.toUpperCase(), ctx);

    MiddlewareChain<String, String> original = new MiddlewareChain<>();
    original.use(middleware);

    MiddlewareChain<String, String> copy = original.copy();

    // Both should work
    String result1 = original.execute("hello", context, (ctx, req) -> "Result: " + req);
    String result2 = copy.execute("world", context, (ctx, req) -> "Result: " + req);

    assertEquals("Result: HELLO", result1);
    assertEquals("Result: WORLD", result2);
  }

  @Test
  void testUseFirst() {
    List<String> order = new ArrayList<>();

    Middleware<String, String> first = (request, ctx, next) -> {
      order.add("first");
      return next.apply(request, ctx);
    };

    Middleware<String, String> second = (request, ctx, next) -> {
      order.add("second");
      return next.apply(request, ctx);
    };

    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    chain.use(first);
    chain.useFirst(second);

    chain.execute("hello", context, (ctx, req) -> "Result: " + req);

    assertEquals(List.of("second", "first"), order);
  }

  @Test
  void testChainSize() {
    MiddlewareChain<String, String> chain = new MiddlewareChain<>();
    assertEquals(0, chain.size());
    assertTrue(chain.isEmpty());

    chain.use((request, ctx, next) -> next.apply(request, ctx));
    assertEquals(1, chain.size());
    assertFalse(chain.isEmpty());

    chain.clear();
    assertEquals(0, chain.size());
    assertTrue(chain.isEmpty());
  }
}

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

package com.google.genkit.core;

import static org.junit.jupiter.api.Assertions.*;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for GenkitException.
 */
class GenkitExceptionTest {

  @Test
  void testConstructorWithMessageOnly() {
    String message = "Test error message";

    GenkitException exception = new GenkitException(message);

    assertEquals(message, exception.getMessage());
    assertNull(exception.getCause());
    assertNull(exception.getErrorCode());
    assertNull(exception.getDetails());
    assertNull(exception.getTraceId());
  }

  @Test
  void testConstructorWithMessageAndCause() {
    String message = "Test error message";
    RuntimeException cause = new RuntimeException("Root cause");

    GenkitException exception = new GenkitException(message, cause);

    assertEquals(message, exception.getMessage());
    assertEquals(cause, exception.getCause());
    assertNull(exception.getErrorCode());
    assertNull(exception.getDetails());
    assertNull(exception.getTraceId());
  }

  @Test
  void testConstructorWithAllParameters() {
    String message = "Test error message";
    RuntimeException cause = new RuntimeException("Root cause");
    String errorCode = "ERR_001";
    Map<String, Object> details = new HashMap<>();
    details.put("field", "value");
    String traceId = "trace-123";

    GenkitException exception = new GenkitException(message, cause, errorCode, details, traceId);

    assertEquals(message, exception.getMessage());
    assertEquals(cause, exception.getCause());
    assertEquals(errorCode, exception.getErrorCode());
    assertEquals(details, exception.getDetails());
    assertEquals(traceId, exception.getTraceId());
  }

  @Test
  void testIsRuntimeException() {
    GenkitException exception = new GenkitException("Test");

    assertTrue(exception instanceof RuntimeException);
  }

  @Test
  void testExceptionCanBeThrown() {
    assertThrows(GenkitException.class, () -> {
      throw new GenkitException("Test exception");
    });
  }

  @Test
  void testExceptionChaining() {
    Exception original = new Exception("Original error");
    GenkitException wrapped = new GenkitException("Wrapped error", original);

    Throwable cause = wrapped.getCause();
    assertNotNull(cause);
    assertEquals("Original error", cause.getMessage());
  }

  @Test
  void testNullCause() {
    GenkitException exception = new GenkitException("Test", null, "ERR", null, null);

    assertNull(exception.getCause());
  }

  @Test
  void testDetailsCanBeAnyObject() {
    String stringDetails = "Simple string details";
    GenkitException exceptionWithString = new GenkitException("Test", null, "ERR", stringDetails, null);
    assertEquals(stringDetails, exceptionWithString.getDetails());

    Map<String, Object> mapDetails = Map.of("key", "value");
    GenkitException exceptionWithMap = new GenkitException("Test", null, "ERR", mapDetails, null);
    assertEquals(mapDetails, exceptionWithMap.getDetails());
  }

  @Test
  void testStackTrace() {
    GenkitException exception = new GenkitException("Test");

    StackTraceElement[] stackTrace = exception.getStackTrace();
    assertNotNull(stackTrace);
    assertTrue(stackTrace.length > 0);
  }

  @Test
  void testToString() {
    GenkitException exception = new GenkitException("Test message");

    String string = exception.toString();
    assertNotNull(string);
    assertTrue(string.contains("GenkitException"));
    assertTrue(string.contains("Test message"));
  }
}

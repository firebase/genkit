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

package com.google.genkit.ai;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for Media.
 */
class MediaTest {

  @Test
  void testDefaultConstructor() {
    Media media = new Media();

    assertNull(media.getContentType());
    assertNull(media.getUrl());
  }

  @Test
  void testConstructorWithParameters() {
    Media media = new Media("image/png", "http://example.com/image.png");

    assertEquals("image/png", media.getContentType());
    assertEquals("http://example.com/image.png", media.getUrl());
  }

  @Test
  void testSetContentType() {
    Media media = new Media();
    media.setContentType("video/mp4");

    assertEquals("video/mp4", media.getContentType());
  }

  @Test
  void testSetUrl() {
    Media media = new Media();
    media.setUrl("http://example.com/video.mp4");

    assertEquals("http://example.com/video.mp4", media.getUrl());
  }

  @Test
  void testCommonMediaTypes() {
    Media png = new Media("image/png", "http://example.com/img.png");
    Media jpeg = new Media("image/jpeg", "http://example.com/img.jpg");
    Media gif = new Media("image/gif", "http://example.com/img.gif");
    Media webp = new Media("image/webp", "http://example.com/img.webp");
    Media pdf = new Media("application/pdf", "http://example.com/doc.pdf");
    Media mp3 = new Media("audio/mpeg", "http://example.com/audio.mp3");
    Media mp4 = new Media("video/mp4", "http://example.com/video.mp4");

    assertEquals("image/png", png.getContentType());
    assertEquals("image/jpeg", jpeg.getContentType());
    assertEquals("image/gif", gif.getContentType());
    assertEquals("image/webp", webp.getContentType());
    assertEquals("application/pdf", pdf.getContentType());
    assertEquals("audio/mpeg", mp3.getContentType());
    assertEquals("video/mp4", mp4.getContentType());
  }

  @Test
  void testDataUrl() {
    String dataUrl = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
    Media media = new Media("image/png", dataUrl);

    assertEquals("image/png", media.getContentType());
    assertTrue(media.getUrl().startsWith("data:"));
  }

  @Test
  void testHttpsUrl() {
    Media media = new Media("image/png", "https://secure.example.com/image.png");

    assertTrue(media.getUrl().startsWith("https://"));
  }

  @Test
  void testRelativeUrl() {
    Media media = new Media("image/png", "/images/photo.png");

    assertEquals("/images/photo.png", media.getUrl());
  }

  @Test
  void testNullValues() {
    Media media = new Media(null, null);

    assertNull(media.getContentType());
    assertNull(media.getUrl());
  }

  @Test
  void testEmptyValues() {
    Media media = new Media("", "");

    assertEquals("", media.getContentType());
    assertEquals("", media.getUrl());
  }

  @Test
  void testMutableProperties() {
    Media media = new Media("image/png", "http://old.url.com/img.png");

    media.setContentType("image/jpeg");
    media.setUrl("http://new.url.com/img.jpg");

    assertEquals("image/jpeg", media.getContentType());
    assertEquals("http://new.url.com/img.jpg", media.getUrl());
  }
}

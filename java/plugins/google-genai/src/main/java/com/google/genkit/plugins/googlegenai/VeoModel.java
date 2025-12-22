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

package com.google.genkit.plugins.googlegenai;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genai.Client;
import com.google.genai.types.GenerateVideosConfig;
import com.google.genai.types.GenerateVideosOperation;
import com.google.genai.types.GenerateVideosResponse;
import com.google.genai.types.GenerateVideosSource;
import com.google.genai.types.GeneratedVideo;
import com.google.genai.types.HttpOptions;
import com.google.genai.types.Video;
import com.google.genkit.ai.Candidate;
import com.google.genkit.ai.FinishReason;
import com.google.genkit.ai.Media;
import com.google.genkit.ai.Message;
import com.google.genkit.ai.Model;
import com.google.genkit.ai.ModelInfo;
import com.google.genkit.ai.ModelRequest;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.ModelResponseChunk;
import com.google.genkit.ai.Part;
import com.google.genkit.ai.Role;
import com.google.genkit.core.ActionContext;
import com.google.genkit.core.GenkitException;

/**
 * Video generation model using Google Veo.
 *
 * <p>
 * This model generates videos using Google's Veo video generation models. Veo
 * supports both text-to-video and image-to-video generation.
 *
 * <p>
 * Supported models:
 * <ul>
 * <li>veo-2.0-generate-001</li>
 * <li>veo-3.0-generate-001</li>
 * <li>veo-3.0-fast-generate-001</li>
 * <li>veo-3.1-generate-preview</li>
 * <li>veo-3.1-fast-generate-preview</li>
 * </ul>
 *
 * <p>
 * Configuration options (via custom config):
 * <ul>
 * <li>numberOfVideos - Number of videos to generate (1-4, default: 1)</li>
 * <li>durationSeconds - Video duration (5-8 seconds, default: 5)</li>
 * <li>aspectRatio - Aspect ratio (16:9 or 9:16, default: 16:9)</li>
 * <li>personGeneration - Allow person generation (allowed/disallowed)</li>
 * <li>negativePrompt - Negative prompt for generation</li>
 * <li>enhancePrompt - Enable prompt enhancement (default: true)</li>
 * <li>seed - Random seed for reproducibility</li>
 * <li>outputGcsUri - GCS URI for output</li>
 * <li>generateAudio - Generate audio with video (veo-3.0+ only)</li>
 * <li>pollIntervalMs - Polling interval in ms (default: 5000)</li>
 * <li>timeoutMs - Operation timeout in ms (default: 300000)</li>
 * </ul>
 */
public class VeoModel implements Model {

  private static final Logger logger = LoggerFactory.getLogger(VeoModel.class);

  private static final Set<String> SUPPORTED_VEO_MODELS = Set.of("veo-2.0-generate-001", "veo-3.0-generate-001",
      "veo-3.0-fast-generate-001", "veo-3.1-generate-preview", "veo-3.1-fast-generate-preview");

  private static final long DEFAULT_POLL_INTERVAL_MS = 5000;
  private static final long DEFAULT_TIMEOUT_MS = 300000; // 5 minutes

  private final String modelName;
  private final GoogleGenAIPluginOptions options;
  private final Client client;
  private final ModelInfo info;

  /**
   * Creates a VeoModel for the specified model.
   *
   * @param modelName
   *            the Veo model name
   * @param options
   *            the plugin options
   */
  public VeoModel(String modelName, GoogleGenAIPluginOptions options) {
    this.modelName = modelName;
    this.options = options;
    this.client = createClient();
    this.info = createModelInfo();
    logger.debug("Initialized Veo model: {}", modelName);
  }

  private Client createClient() {
    Client.Builder builder = Client.builder();

    if (options.isVertexAI()) {
      builder.vertexAI(true);
      if (options.getProject() != null) {
        builder.project(options.getProject());
      }
      if (options.getLocation() != null) {
        builder.location(options.getLocation());
      }
      if (options.getApiKey() != null) {
        builder.apiKey(options.getApiKey());
      }
    } else {
      builder.apiKey(options.getApiKey());
    }

    // Use a longer timeout for video generation operations (10 minutes)
    // Video generation involves long-polling operations that can take several
    // minutes
    HttpOptions.Builder httpBuilder = HttpOptions.builder();
    if (options.getApiVersion() != null) {
      httpBuilder.apiVersion(options.getApiVersion());
    }
    if (options.getBaseUrl() != null) {
      httpBuilder.baseUrl(options.getBaseUrl());
    }
    // Set a 10-minute timeout for HTTP operations
    httpBuilder.timeout(600000);
    builder.httpOptions(httpBuilder.build());

    return builder.build();
  }

  private ModelInfo createModelInfo() {
    ModelInfo info = new ModelInfo();
    info.setLabel("Google Veo " + modelName);

    ModelInfo.ModelCapabilities caps = new ModelInfo.ModelCapabilities();
    caps.setMultiturn(false);
    caps.setMedia(true); // Supports image input for image-to-video
    caps.setTools(false);
    caps.setSystemRole(false);
    caps.setOutput(Set.of("media"));
    info.setSupports(caps);

    return info;
  }

  @Override
  public String getName() {
    return "googleai/" + modelName;
  }

  @Override
  public ModelInfo getInfo() {
    return info;
  }

  @Override
  public boolean supportsStreaming() {
    return false; // Video generation doesn't support streaming
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request) {
    try {
      return generateVideo(request);
    } catch (Exception e) {
      throw new GenkitException("Video generation failed: " + e.getMessage(), e);
    }
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request, Consumer<ModelResponseChunk> streamCallback) {
    // Video generation doesn't support streaming
    return run(context, request);
  }

  private ModelResponse generateVideo(ModelRequest request) throws Exception {
    String prompt = extractPrompt(request);
    GenerateVideosConfig config = buildConfig(request);
    GenerateVideosSource source = buildSource(request, prompt);

    logger.debug("Calling Veo model {} with prompt: {}", modelName,
        prompt.substring(0, Math.min(100, prompt.length())));

    // Start video generation operation
    GenerateVideosOperation operation = client.models.generateVideos(modelName, source, config);

    // Poll for completion
    Map<String, Object> customConfig = request.getConfig();
    long pollIntervalMs = DEFAULT_POLL_INTERVAL_MS;
    long timeoutMs = DEFAULT_TIMEOUT_MS;

    if (customConfig != null) {
      if (customConfig.containsKey("pollIntervalMs")) {
        pollIntervalMs = ((Number) customConfig.get("pollIntervalMs")).longValue();
      }
      if (customConfig.containsKey("timeoutMs")) {
        timeoutMs = ((Number) customConfig.get("timeoutMs")).longValue();
      }
    }

    GenerateVideosResponse response = pollForCompletion(operation, pollIntervalMs, timeoutMs);

    return parseResponse(response);
  }

  private GenerateVideosResponse pollForCompletion(GenerateVideosOperation operation, long pollIntervalMs,
      long timeoutMs) throws Exception {
    long startTime = System.currentTimeMillis();
    String operationName = operation.name().orElse("");

    while (true) {
      // Check if done
      if (operation.done().orElse(false)) {
        logger.debug("Video generation completed for operation: {}", operationName);
        if (operation.response().isPresent()) {
          return operation.response().get();
        }
        // Check for error
        if (operation.error().isPresent()) {
          Map<String, Object> error = operation.error().get();
          String errorMsg = error.containsKey("message")
              ? String.valueOf(error.get("message"))
              : "Unknown error";
          throw new GenkitException("Video generation failed: " + errorMsg);
        }
        throw new GenkitException("Video generation completed but no response");
      }

      // Check timeout
      if (System.currentTimeMillis() - startTime > timeoutMs) {
        throw new GenkitException("Video generation timed out after " + timeoutMs + "ms");
      }

      // Sleep and poll again
      Thread.sleep(pollIntervalMs);
      operation = client.operations.getVideosOperation(operation, null);
    }
  }

  private String extractPrompt(ModelRequest request) {
    StringBuilder prompt = new StringBuilder();

    if (request.getMessages() != null) {
      for (Message message : request.getMessages()) {
        if (message.getContent() != null) {
          for (Part part : message.getContent()) {
            if (part.getText() != null) {
              if (prompt.length() > 0) {
                prompt.append("\n");
              }
              prompt.append(part.getText());
            }
          }
        }
      }
    }

    return prompt.toString();
  }

  private GenerateVideosSource buildSource(ModelRequest request, String prompt) {
    GenerateVideosSource.Builder sourceBuilder = GenerateVideosSource.builder();
    sourceBuilder.prompt(prompt);

    // Look for image in the messages for image-to-video
    if (request.getMessages() != null) {
      for (Message message : request.getMessages()) {
        if (message.getContent() != null) {
          for (Part part : message.getContent()) {
            if (part.getMedia() != null) {
              Media media = part.getMedia();
              String contentType = media.getContentType();
              if (contentType != null && contentType.startsWith("image/")) {
                com.google.genai.types.Image image = createImage(media);
                if (image != null) {
                  sourceBuilder.image(image);
                  logger.debug("Added reference image for image-to-video generation");
                }
              }
            }
          }
        }
      }
    }

    return sourceBuilder.build();
  }

  private com.google.genai.types.Image createImage(Media media) {
    com.google.genai.types.Image.Builder builder = com.google.genai.types.Image.builder();

    String url = media.getUrl();
    if (url != null) {
      if (url.startsWith("data:")) {
        // Parse data URL
        int commaIndex = url.indexOf(',');
        if (commaIndex > 0) {
          String base64Data = url.substring(commaIndex + 1);
          byte[] imageBytes = Base64.getDecoder().decode(base64Data);
          builder.imageBytes(imageBytes);

          // Extract mime type
          String header = url.substring(5, commaIndex);
          int semiIndex = header.indexOf(';');
          if (semiIndex > 0) {
            builder.mimeType(header.substring(0, semiIndex));
          }
        }
      } else if (url.startsWith("gs://")) {
        builder.gcsUri(url);
      }
      // Note: HTTP URLs not directly supported by Image.Builder
      // Would need to download and use imageBytes instead
    }

    return builder.build();
  }

  @SuppressWarnings("unchecked")
  private GenerateVideosConfig buildConfig(ModelRequest request) {
    GenerateVideosConfig.Builder configBuilder = GenerateVideosConfig.builder();

    Map<String, Object> config = request.getConfig();
    if (config != null) {
      // Number of videos
      if (config.containsKey("numberOfVideos")) {
        configBuilder.numberOfVideos(((Number) config.get("numberOfVideos")).intValue());
      }

      // Duration (5-8 seconds)
      if (config.containsKey("durationSeconds")) {
        configBuilder.durationSeconds(((Number) config.get("durationSeconds")).intValue());
      }

      // Aspect ratio
      if (config.containsKey("aspectRatio")) {
        configBuilder.aspectRatio((String) config.get("aspectRatio"));
      }

      // Person generation
      if (config.containsKey("personGeneration")) {
        configBuilder.personGeneration((String) config.get("personGeneration"));
      }

      // Negative prompt
      if (config.containsKey("negativePrompt")) {
        configBuilder.negativePrompt((String) config.get("negativePrompt"));
      }

      // Enhance prompt
      if (config.containsKey("enhancePrompt")) {
        configBuilder.enhancePrompt((Boolean) config.get("enhancePrompt"));
      }

      // Seed
      if (config.containsKey("seed")) {
        configBuilder.seed(((Number) config.get("seed")).intValue());
      }

      // Output GCS URI
      if (config.containsKey("outputGcsUri")) {
        configBuilder.outputGcsUri((String) config.get("outputGcsUri"));
      }

      // Generate audio (veo-3.0+ only)
      if (config.containsKey("generateAudio")) {
        configBuilder.generateAudio((Boolean) config.get("generateAudio"));
      }
    }

    return configBuilder.build();
  }

  private ModelResponse parseResponse(GenerateVideosResponse response) {
    ModelResponse modelResponse = new ModelResponse();
    List<Candidate> candidates = new ArrayList<>();
    Candidate candidate = new Candidate();
    Message message = new Message();
    message.setRole(Role.MODEL);
    List<Part> parts = new ArrayList<>();

    // Log the raw response for debugging
    logger.info("Video response: generatedVideos present={}", response.generatedVideos().isPresent());
    if (response.generatedVideos().isPresent()) {
      logger.info("Number of generated videos: {}", response.generatedVideos().get().size());
    }

    // Extract generated videos
    if (response.generatedVideos().isPresent()) {
      for (GeneratedVideo generatedVideo : response.generatedVideos().get()) {
        logger.info("GeneratedVideo: video present={}", generatedVideo.video().isPresent());
        if (generatedVideo.video().isPresent()) {
          Video video = generatedVideo.video().get();
          logger.info("Video: uri={}, videoBytes present={}, mimeType={}", video.uri().orElse("none"),
              video.videoBytes().isPresent(), video.mimeType().orElse("none"));
          Part videoPart = createVideoPart(video);
          if (videoPart != null) {
            parts.add(videoPart);
          }
        }
      }
    }

    if (!parts.isEmpty()) {
      logger.debug("Generated {} video(s)", parts.size());
    } else {
      logger.warn("No videos generated in response");
    }

    message.setContent(parts);
    candidate.setMessage(message);
    candidate.setFinishReason(FinishReason.STOP);
    candidate.setIndex(0);
    candidates.add(candidate);

    modelResponse.setCandidates(candidates);
    modelResponse.setFinishReason(FinishReason.STOP);

    return modelResponse;
  }

  private Part createVideoPart(Video video) {
    Part part = new Part();
    Media media = new Media();

    // Check for video bytes first
    if (video.videoBytes().isPresent()) {
      byte[] videoBytes = video.videoBytes().get();
      String base64 = Base64.getEncoder().encodeToString(videoBytes);
      String mimeType = video.mimeType().orElse("video/mp4");
      media.setContentType(mimeType);
      media.setUrl("data:" + mimeType + ";base64," + base64);
      logger.debug("Created video part with {} bytes", videoBytes.length);
    } else if (video.uri().isPresent()) {
      String uri = video.uri().get();

      // If it's an HTTP(S) URL, download the video and convert to base64
      if (uri.startsWith("http://") || uri.startsWith("https://")) {
        try {
          byte[] videoBytes = downloadVideo(uri);
          String base64 = Base64.getEncoder().encodeToString(videoBytes);
          String mimeType = video.mimeType().orElse("video/mp4");
          media.setContentType(mimeType);
          media.setUrl("data:" + mimeType + ";base64," + base64);
          logger.info("Downloaded and encoded video from URL, {} bytes", videoBytes.length);
        } catch (Exception e) {
          logger.warn("Failed to download video from URL: {}, using URL directly", uri, e);
          media.setUrl(uri);
          media.setContentType(video.mimeType().orElse("video/mp4"));
        }
      } else {
        // Use URI directly (e.g., gs:// URLs)
        media.setUrl(uri);
        media.setContentType(video.mimeType().orElse("video/mp4"));
        logger.debug("Created video part with URI: {}", uri);
      }
    } else {
      logger.warn("Video has neither bytes nor URI");
      return null;
    }

    part.setMedia(media);
    return part;
  }

  private byte[] downloadVideo(String urlString) throws Exception {
    // Append API key to URL for authentication
    String authenticatedUrl = urlString;
    if (options.getApiKey() != null && !options.isVertexAI()) {
      String separator = urlString.contains("?") ? "&" : "?";
      authenticatedUrl = urlString + separator + "key=" + options.getApiKey();
    }

    URL url = new URL(authenticatedUrl);
    HttpURLConnection connection = (HttpURLConnection) url.openConnection();
    connection.setRequestMethod("GET");
    connection.setConnectTimeout(30000);
    connection.setReadTimeout(300000); // 5 minutes for large videos

    try (InputStream in = connection.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
      byte[] buffer = new byte[8192];
      int bytesRead;
      while ((bytesRead = in.read(buffer)) != -1) {
        out.write(buffer, 0, bytesRead);
      }
      return out.toByteArray();
    } finally {
      connection.disconnect();
    }
  }

  /**
   * Checks if the given model name is a supported Veo model.
   *
   * @param modelName
   *            the model name to check
   * @return true if the model is a Veo model
   */
  public static boolean isVeoModel(String modelName) {
    return SUPPORTED_VEO_MODELS.contains(modelName) || modelName.startsWith("veo-");
  }
}

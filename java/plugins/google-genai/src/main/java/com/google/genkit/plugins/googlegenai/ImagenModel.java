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

import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.genai.Client;
import com.google.genai.types.GenerateImagesConfig;
import com.google.genai.types.GenerateImagesResponse;
import com.google.genai.types.GeneratedImage;
import com.google.genai.types.HttpOptions;
import com.google.genai.types.Image;
import com.google.genai.types.PersonGeneration;
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
 * Imagen model implementation for image generation using the official Google
 * GenAI SDK.
 *
 * <p>
 * Imagen is Google's text-to-image model that generates high-quality images
 * from text prompts.
 *
 * <p>
 * Configuration options (passed via request.config):
 * <ul>
 * <li>numberOfImages - Number of images to generate (1-4)</li>
 * <li>aspectRatio - Aspect ratio: "1:1", "3:4", "4:3", "9:16", "16:9"</li>
 * <li>personGeneration - Control people generation: "dont_allow",
 * "allow_adult", "allow_all"</li>
 * <li>negativePrompt - Description of what to avoid in the generated
 * images</li>
 * <li>outputMimeType - MIME type of output: "image/png" or "image/jpeg"</li>
 * </ul>
 */
public class ImagenModel implements Model {

  private static final Logger logger = LoggerFactory.getLogger(ImagenModel.class);

  private final String modelName;
  private final GoogleGenAIPluginOptions options;
  private final Client client;
  private final ModelInfo info;

  /**
   * Creates a new ImagenModel.
   *
   * @param modelName
   *            the model name (e.g., "imagen-3.0-generate-002")
   * @param options
   *            the plugin options
   */
  public ImagenModel(String modelName, GoogleGenAIPluginOptions options) {
    this.modelName = modelName;
    this.options = options;
    this.client = createClient();
    this.info = createModelInfo();
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

    HttpOptions httpOptions = options.toHttpOptions();
    if (httpOptions != null) {
      builder.httpOptions(httpOptions);
    }

    return builder.build();
  }

  private ModelInfo createModelInfo() {
    ModelInfo info = new ModelInfo();
    info.setLabel("Google AI " + modelName);

    ModelInfo.ModelCapabilities caps = new ModelInfo.ModelCapabilities();
    caps.setMultiturn(false); // Image generation is single-turn
    caps.setMedia(true); // Input can include reference images
    caps.setTools(false); // No tool support
    caps.setSystemRole(false); // No system role
    caps.setOutput(Set.of("media")); // Outputs media (images)
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
    return false; // Image generation doesn't support streaming
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request) {
    try {
      return generateImages(request);
    } catch (Exception e) {
      throw new GenkitException("Imagen API call failed: " + e.getMessage(), e);
    }
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request, Consumer<ModelResponseChunk> streamCallback) {
    // Image generation doesn't support streaming, just call the regular method
    return run(context, request);
  }

  private ModelResponse generateImages(ModelRequest request) {
    String prompt = extractPrompt(request);
    if (prompt == null || prompt.isEmpty()) {
      throw new GenkitException("Prompt is required for image generation");
    }

    GenerateImagesConfig config = buildConfig(request);

    logger.debug("Generating images with model {} and prompt: {}", modelName, prompt);

    GenerateImagesResponse response = client.models.generateImages(modelName, prompt, config);

    return parseResponse(response);
  }

  private String extractPrompt(ModelRequest request) {
    if (request.getMessages() == null || request.getMessages().isEmpty()) {
      return null;
    }

    // Get the last user message
    for (int i = request.getMessages().size() - 1; i >= 0; i--) {
      Message msg = request.getMessages().get(i);
      if (msg.getRole() == Role.USER) {
        return msg.getText();
      }
    }

    return null;
  }

  private GenerateImagesConfig buildConfig(ModelRequest request) {
    GenerateImagesConfig.Builder configBuilder = GenerateImagesConfig.builder();

    Map<String, Object> config = request.getConfig();
    if (config == null) {
      // Default config
      configBuilder.numberOfImages(1);
      configBuilder.outputMimeType("image/png");
      return configBuilder.build();
    }

    // Number of images
    if (config.containsKey("numberOfImages")) {
      configBuilder.numberOfImages(((Number) config.get("numberOfImages")).intValue());
    } else {
      configBuilder.numberOfImages(1);
    }

    // Aspect ratio
    if (config.containsKey("aspectRatio")) {
      configBuilder.aspectRatio((String) config.get("aspectRatio"));
    }

    // Person generation
    if (config.containsKey("personGeneration")) {
      String personGen = (String) config.get("personGeneration");
      switch (personGen.toLowerCase()) {
        case "dont_allow" :
        case "allow_none" :
          configBuilder.personGeneration(PersonGeneration.Known.DONT_ALLOW);
          break;
        case "allow_adult" :
          configBuilder.personGeneration(PersonGeneration.Known.ALLOW_ADULT);
          break;
        case "allow_all" :
          configBuilder.personGeneration(PersonGeneration.Known.ALLOW_ALL);
          break;
        default :
          configBuilder.personGeneration(personGen);
      }
    }

    // Negative prompt
    if (config.containsKey("negativePrompt")) {
      configBuilder.negativePrompt((String) config.get("negativePrompt"));
    }

    // Output MIME type
    if (config.containsKey("outputMimeType")) {
      configBuilder.outputMimeType((String) config.get("outputMimeType"));
    } else {
      configBuilder.outputMimeType("image/png");
    }

    // Safety filter level
    if (config.containsKey("safetyFilterLevel")) {
      configBuilder.safetyFilterLevel((String) config.get("safetyFilterLevel"));
    }

    // Include safety attributes
    if (config.containsKey("includeSafetyAttributes")) {
      configBuilder.includeSafetyAttributes((Boolean) config.get("includeSafetyAttributes"));
    }

    // Guidance scale
    if (config.containsKey("guidanceScale")) {
      configBuilder.guidanceScale(((Number) config.get("guidanceScale")).floatValue());
    }

    // Seed
    if (config.containsKey("seed")) {
      configBuilder.seed(((Number) config.get("seed")).intValue());
    }

    return configBuilder.build();
  }

  private ModelResponse parseResponse(GenerateImagesResponse response) {
    ModelResponse modelResponse = new ModelResponse();
    List<com.google.genkit.ai.Candidate> candidates = new ArrayList<>();
    com.google.genkit.ai.Candidate candidate = new com.google.genkit.ai.Candidate();

    Message message = new Message();
    message.setRole(Role.MODEL);
    List<Part> parts = new ArrayList<>();

    // Get generated images
    if (response.generatedImages().isPresent()) {
      List<GeneratedImage> generatedImages = response.generatedImages().get();

      for (GeneratedImage genImage : generatedImages) {
        if (genImage.image().isPresent()) {
          Image image = genImage.image().get();
          Part imagePart = createImagePart(image);
          if (imagePart != null) {
            parts.add(imagePart);
          }
        }
      }

      logger.debug("Generated {} images", generatedImages.size());
    } else {
      logger.warn("No images generated in response");
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

  private Part createImagePart(Image image) {
    Part part = new Part();

    // Image can have either imageBytes or gcsUri
    if (image.imageBytes().isPresent()) {
      byte[] imageBytes = image.imageBytes().get();
      String base64 = Base64.getEncoder().encodeToString(imageBytes);
      String mimeType = image.mimeType().orElse("image/png");

      Media media = new Media();
      media.setUrl("data:" + mimeType + ";base64," + base64);
      media.setContentType(mimeType);
      part.setMedia(media);

      return part;
    } else if (image.gcsUri().isPresent()) {
      String gcsUri = image.gcsUri().get();
      String mimeType = image.mimeType().orElse("image/png");

      Media media = new Media();
      media.setUrl(gcsUri);
      media.setContentType(mimeType);
      part.setMedia(media);

      return part;
    }

    return null;
  }
}

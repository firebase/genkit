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
import com.google.genai.types.Content;
import com.google.genai.types.GenerateContentConfig;
import com.google.genai.types.GenerateContentResponse;
import com.google.genai.types.HttpOptions;
import com.google.genai.types.PrebuiltVoiceConfig;
import com.google.genai.types.SpeechConfig;
import com.google.genai.types.VoiceConfig;
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
 * Text-to-Speech model using Gemini TTS models.
 *
 * <p>
 * This model uses Gemini's TTS capabilities via responseModalities=AUDIO and
 * speechConfig for voice configuration.
 *
 * <p>
 * Supported models:
 * <ul>
 * <li>gemini-2.5-flash-preview-tts</li>
 * <li>gemini-2.5-pro-preview-tts</li>
 * </ul>
 *
 * <p>
 * Configuration options (via custom config):
 * <ul>
 * <li>voiceName - Name of the voice to use (e.g., "Zephyr", "Puck", "Charon",
 * "Kore", etc.)</li>
 * </ul>
 *
 * <p>
 * Available voices: Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede,
 * Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome,
 * Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux,
 * Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager,
 * Sulafat
 */
public class TtsModel implements Model {

  private static final Logger logger = LoggerFactory.getLogger(TtsModel.class);

  private static final Set<String> SUPPORTED_TTS_MODELS = Set.of("gemini-2.5-flash-preview-tts",
      "gemini-2.5-pro-preview-tts");

  private final String modelName;
  private final GoogleGenAIPluginOptions options;
  private final Client client;
  private final ModelInfo info;

  /**
   * Creates a TtsModel for the specified model.
   *
   * @param modelName
   *            the TTS model name
   * @param options
   *            the plugin options
   */
  public TtsModel(String modelName, GoogleGenAIPluginOptions options) {
    this.modelName = modelName;
    this.options = options;
    this.client = createClient();
    this.info = createModelInfo();
    logger.debug("Initialized TTS model: {}", modelName);
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
    info.setLabel("Google AI TTS " + modelName);

    ModelInfo.ModelCapabilities caps = new ModelInfo.ModelCapabilities();
    caps.setMultiturn(false);
    caps.setMedia(false);
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
    return false; // TTS doesn't support streaming in the same way
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request) {
    try {
      return callTts(request);
    } catch (Exception e) {
      throw new GenkitException("TTS API call failed: " + e.getMessage(), e);
    }
  }

  @Override
  public ModelResponse run(ActionContext context, ModelRequest request, Consumer<ModelResponseChunk> streamCallback) {
    // TTS doesn't support streaming - just return final audio
    return run(context, request);
  }

  private ModelResponse callTts(ModelRequest request) throws Exception {
    String prompt = extractPrompt(request);
    GenerateContentConfig config = buildConfig(request);

    logger.debug("Calling TTS model {} with prompt length: {}", modelName, prompt.length());

    GenerateContentResponse response = client.models.generateContent(modelName, prompt, config);

    return parseResponse(response);
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

  @SuppressWarnings("unchecked")
  private GenerateContentConfig buildConfig(ModelRequest request) {
    GenerateContentConfig.Builder configBuilder = GenerateContentConfig.builder();

    // Set response modalities to AUDIO
    configBuilder.responseModalities("AUDIO");

    // Build speech config
    SpeechConfig.Builder speechConfigBuilder = SpeechConfig.builder();

    // Check for voice configuration in custom config
    Map<String, Object> config = request.getConfig();
    if (config != null) {
      String voiceName = null;
      if (config.containsKey("voiceName")) {
        voiceName = (String) config.get("voiceName");
      }

      if (voiceName != null) {
        VoiceConfig voiceConfig = VoiceConfig.builder()
            .prebuiltVoiceConfig(PrebuiltVoiceConfig.builder().voiceName(voiceName).build()).build();
        speechConfigBuilder.voiceConfig(voiceConfig);
      }
    }

    configBuilder.speechConfig(speechConfigBuilder.build());

    return configBuilder.build();
  }

  private ModelResponse parseResponse(GenerateContentResponse response) {
    ModelResponse modelResponse = new ModelResponse();
    List<Candidate> candidates = new ArrayList<>();
    Candidate candidate = new Candidate();
    Message message = new Message();
    message.setRole(Role.MODEL);
    List<Part> parts = new ArrayList<>();

    // Extract audio parts from response
    if (response.candidates().isPresent()) {
      for (com.google.genai.types.Candidate genaiCandidate : response.candidates().get()) {
        if (genaiCandidate.content().isPresent()) {
          Content content = genaiCandidate.content().get();
          if (content.parts().isPresent()) {
            for (com.google.genai.types.Part genaiPart : content.parts().get()) {
              // Check for inline audio data
              if (genaiPart.inlineData().isPresent()) {
                com.google.genai.types.Blob blob = genaiPart.inlineData().get();
                Part audioPart = createAudioPart(blob);
                if (audioPart != null) {
                  parts.add(audioPart);
                }
              }
            }
          }
        }
      }
    }

    if (!parts.isEmpty()) {
      logger.debug("Generated {} audio part(s)", parts.size());
    } else {
      logger.warn("No audio generated in response");
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

  private Part createAudioPart(com.google.genai.types.Blob blob) {
    Part part = new Part();

    if (blob.data().isPresent()) {
      byte[] audioBytes = blob.data().get();
      String base64 = Base64.getEncoder().encodeToString(audioBytes);
      String mimeType = blob.mimeType().orElse("audio/wav");

      Media media = new Media();
      media.setContentType(mimeType);
      // Create data URL
      media.setUrl("data:" + mimeType + ";base64," + base64);
      part.setMedia(media);

      logger.debug("Created audio part with {} bytes, mime type: {}", audioBytes.length, mimeType);
      return part;
    }

    return null;
  }

  /**
   * Checks if the given model name is a supported TTS model.
   *
   * @param modelName
   *            the model name to check
   * @return true if the model is a TTS model
   */
  public static boolean isTtsModel(String modelName) {
    return SUPPORTED_TTS_MODELS.contains(modelName)
        || (modelName.startsWith("gemini-") && modelName.endsWith("-tts"));
  }
}

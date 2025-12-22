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

package com.google.genkit.samples;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.*;
import com.google.genkit.ai.session.*;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Sample application demonstrating session-based multi-turn conversations.
 *
 * This example shows how to: - Create sessions with persistent state - Conduct
 * multi-turn conversations with automatic history management - Use multiple
 * conversation threads within a session - Implement custom session stores for
 * persistence - Use tools within session-based chats
 *
 * To run: 1. Set the OPENAI_API_KEY environment variable 2. Run: mvn exec:java
 * -Dexec.mainClass=com.google.genkit.samples.SessionSample
 */
public class SessionSample {

  /**
   * Custom session state to track user preferences and conversation context.
   */
  public static class UserState {
    private String userName;
    private String preferredLanguage;
    private int messageCount;

    public UserState() {
    }

    public UserState(String userName) {
      this.userName = userName;
      this.preferredLanguage = "English";
      this.messageCount = 0;
    }

    public String getUserName() {
      return userName;
    }

    public void setUserName(String userName) {
      this.userName = userName;
    }

    public String getPreferredLanguage() {
      return preferredLanguage;
    }

    public void setPreferredLanguage(String preferredLanguage) {
      this.preferredLanguage = preferredLanguage;
    }

    public int getMessageCount() {
      return messageCount;
    }

    public void incrementMessageCount() {
      this.messageCount++;
    }
  }

  public static void main(String[] args) throws Exception {
    // Create Genkit with OpenAI plugin
    Genkit genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).build();

    // Define a tool for the conversation
    @SuppressWarnings("unchecked")
    Tool<Map<String, Object>, Map<String, Object>> reminderTool = genkit.defineTool("setReminder",
        "Sets a reminder for the user",
        Map.of("type", "object", "properties",
            Map.of("message", Map.of("type", "string", "description", "The reminder message"), "time",
                Map.of("type", "string", "description",
                    "When to remind (e.g., '5 minutes', 'tomorrow')")),
            "required", new String[]{"message", "time"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          Map<String, Object> result = new HashMap<>();
          result.put("status", "success");
          result.put("message", "Reminder set: " + input.get("message") + " at " + input.get("time"));
          return result;
        });

    System.out.println("=== Session-Based Chat Demo ===\n");

    // Example 1: Basic session with multi-turn conversation
    basicSessionExample(genkit);

    // Example 2: Session with custom state
    sessionWithStateExample(genkit);

    // Example 3: Multiple conversation threads
    multiThreadExample(genkit);

    // Example 4: Session with tools
    sessionWithToolsExample(genkit, reminderTool);

    // Example 5: Loading existing sessions
    sessionPersistenceExample(genkit);

    System.out.println("\n=== Demo Complete ===");
  }

  /**
   * Demonstrates basic session creation and multi-turn conversation.
   */
  private static void basicSessionExample(Genkit genkit) throws Exception {
    System.out.println("--- Example 1: Basic Multi-Turn Conversation ---\n");

    // Create a session
    Session<Void> session = genkit.createSession();
    System.out.println("Created session: " + session.getId());

    // Create a chat with system prompt
    Chat<Void> chat = session.chat(ChatOptions.<Void>builder().model("openai/gpt-4o-mini")
        .system("You are a helpful assistant. Keep your responses brief and friendly.").build());

    // Multi-turn conversation - history is automatically managed
    System.out.println("\nUser: What is the capital of France?");
    ModelResponse response1 = chat.send("What is the capital of France?");
    System.out.println("Assistant: " + response1.getText());

    System.out.println("\nUser: What's the population?");
    ModelResponse response2 = chat.send("What's the population?");
    System.out.println("Assistant: " + response2.getText());

    System.out.println("\nUser: What language do they speak there?");
    ModelResponse response3 = chat.send("What language do they speak there?");
    System.out.println("Assistant: " + response3.getText());

    // Show conversation history
    System.out.println("\n--- Conversation History ---");
    for (Message msg : chat.getHistory()) {
      System.out.println(
          msg.getRole() + ": " + msg.getText().substring(0, Math.min(50, msg.getText().length())) + "...");
    }
    System.out.println();
  }

  /**
   * Demonstrates session with custom state management.
   */
  private static void sessionWithStateExample(Genkit genkit) throws Exception {
    System.out.println("--- Example 2: Session with Custom State ---\n");

    // Create session with initial state
    Session<UserState> session = genkit
        .createSession(SessionOptions.<UserState>builder().initialState(new UserState("Alice")).build());

    System.out.println("Created session for user: " + session.getState().getUserName());

    // Create chat
    Chat<UserState> chat = session.chat(ChatOptions.<UserState>builder().model("openai/gpt-4o-mini")
        .system("You are a helpful assistant. The user's name is " + session.getState().getUserName() + ".")
        .build());

    // Send message and update state
    ModelResponse response = chat.send("Hello! Can you remember my name?");
    System.out.println("Assistant: " + response.getText());

    // Update session state
    UserState state = session.getState();
    state.incrementMessageCount();
    session.updateState(state).join();

    System.out.println("Message count: " + session.getState().getMessageCount());
    System.out.println();
  }

  /**
   * Demonstrates multiple conversation threads within a session.
   */
  private static void multiThreadExample(Genkit genkit) throws Exception {
    System.out.println("--- Example 3: Multiple Conversation Threads ---\n");

    Session<Void> session = genkit.createSession();

    // Create chat for general conversation
    Chat<Void> generalChat = session.chat("general", ChatOptions.<Void>builder().model("openai/gpt-4o-mini")
        .system("You are a helpful general assistant.").build());

    // Create chat for coding help
    Chat<Void> codingChat = session.chat("coding", ChatOptions.<Void>builder().model("openai/gpt-4o-mini")
        .system("You are an expert programmer. Provide concise code examples.").build());

    // Use different threads for different topics
    System.out.println("General thread:");
    ModelResponse generalResponse = generalChat.send("What's a good recipe for pasta?");
    System.out.println("Response: "
        + generalResponse.getText().substring(0, Math.min(100, generalResponse.getText().length())) + "...\n");

    System.out.println("Coding thread:");
    ModelResponse codingResponse = codingChat.send("How do I reverse a string in Java?");
    System.out.println("Response: "
        + codingResponse.getText().substring(0, Math.min(100, codingResponse.getText().length())) + "...\n");

    // Continue in general thread - context is preserved per thread
    System.out.println("Back to general thread:");
    ModelResponse followUp = generalChat.send("What ingredients do I need for that?");
    System.out.println(
        "Response: " + followUp.getText().substring(0, Math.min(100, followUp.getText().length())) + "...\n");
  }

  /**
   * Demonstrates using tools within session-based chats.
   */
  private static void sessionWithToolsExample(Genkit genkit, Tool<?, ?> reminderTool) throws Exception {
    System.out.println("--- Example 4: Session with Tools ---\n");

    Session<Void> session = genkit.createSession();

    @SuppressWarnings("unchecked")
    Chat<Void> chat = session.chat(ChatOptions.<Void>builder().model("openai/gpt-4o-mini")
        .system("You are a helpful assistant that can set reminders for users.")
        .tools(List.of((Tool<?, ?>) reminderTool)).build());

    System.out.println("User: Remind me to buy groceries in 1 hour");
    ModelResponse response = chat.send("Remind me to buy groceries in 1 hour");
    System.out.println("Assistant: " + response.getText());
    System.out.println();
  }

  /**
   * Demonstrates session persistence - saving and loading sessions.
   */
  private static void sessionPersistenceExample(Genkit genkit) throws Exception {
    System.out.println("--- Example 5: Session Persistence ---\n");

    // Create a custom session store (using in-memory for this example)
    InMemorySessionStore<UserState> store = new InMemorySessionStore<>();

    // Create session with the store
    Session<UserState> session = genkit.createSession(SessionOptions.<UserState>builder().store(store)
        .sessionId("persistent-session-001").initialState(new UserState("Bob")).build());

    // Have a conversation
    Chat<UserState> chat = session.chat(ChatOptions.<UserState>builder().model("openai/gpt-4o-mini")
        .system("You are a helpful assistant.").build());

    chat.send("Hello, I'm learning about AI");
    chat.send("What's machine learning?");

    System.out.println("Original session ID: " + session.getId());
    System.out.println("Messages in session: " + chat.getHistory().size());

    // Load the session later (simulating app restart)
    Session<UserState> loadedSession = genkit
        .loadSession("persistent-session-001", SessionOptions.<UserState>builder().store(store).build()).get();

    if (loadedSession != null) {
      System.out.println("\nLoaded session ID: " + loadedSession.getId());
      System.out.println("User name from state: " + loadedSession.getState().getUserName());
      System.out.println("Messages preserved: " + loadedSession.getMessages().size());

      // Continue the conversation
      Chat<UserState> continuedChat = loadedSession.chat(ChatOptions.<UserState>builder()
          .model("openai/gpt-4o-mini").system("You are a helpful assistant.").build());

      System.out.println("\nContinuing conversation...");
      ModelResponse response = continuedChat.send("Can you summarize what we discussed?");
      System.out.println("Assistant: " + response.getText());
    }
    System.out.println();
  }
}

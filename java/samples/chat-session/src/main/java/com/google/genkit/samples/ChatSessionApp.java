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
import java.util.Scanner;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.Message;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.Tool;
import com.google.genkit.ai.session.Chat;
import com.google.genkit.ai.session.ChatOptions;
import com.google.genkit.ai.session.InMemorySessionStore;
import com.google.genkit.ai.session.Session;
import com.google.genkit.ai.session.SessionOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Interactive Chat Application with Session Persistence.
 *
 * <p>
 * This sample demonstrates:
 * <ul>
 * <li>Creating and managing chat sessions</li>
 * <li>Multi-turn conversations with automatic history</li>
 * <li>Session state management</li>
 * <li>Using tools in chat sessions</li>
 * <li>Persisting and loading sessions</li>
 * </ul>
 *
 * <p>
 * To run:
 * <ol>
 * <li>Set the OPENAI_API_KEY environment variable</li>
 * <li>Run: mvn exec:java -pl samples/chat-session</li>
 * </ol>
 */
public class ChatSessionApp {

  /** Session state to track conversation context and user preferences. */
  public static class ConversationState {
    private String userName;
    private String topic;
    private int messageCount;

    public ConversationState() {
      this.messageCount = 0;
    }

    public ConversationState(String userName) {
      this.userName = userName;
      this.messageCount = 0;
    }

    public String getUserName() {
      return userName;
    }

    public void setUserName(String userName) {
      this.userName = userName;
    }

    public String getTopic() {
      return topic;
    }

    public void setTopic(String topic) {
      this.topic = topic;
    }

    public int getMessageCount() {
      return messageCount;
    }

    public void incrementMessageCount() {
      this.messageCount++;
    }

    @Override
    public String toString() {
      return String.format("User: %s, Topic: %s, Messages: %d", userName != null ? userName : "Anonymous",
          topic != null ? topic : "General", messageCount);
    }
  }

  private final Genkit genkit;
  private final InMemorySessionStore<ConversationState> sessionStore;
  private final Tool<?, ?> noteTool;
  private final Map<String, String> notes;

  public ChatSessionApp() {
    // Initialize notes storage
    this.notes = new HashMap<>();

    // Create Genkit with OpenAI plugin
    this.genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3100).build())
        .plugin(OpenAIPlugin.create()).build();

    // Create a shared session store
    this.sessionStore = new InMemorySessionStore<>();

    // Define a note-taking tool
    this.noteTool = createNoteTool();
  }

  @SuppressWarnings("unchecked")
  private Tool<?, ?> createNoteTool() {
    return genkit.defineTool("saveNote",
        "Saves a note for the user. Use this when the user wants to remember something.",
        Map.of("type", "object", "properties",
            Map.of("title", Map.of("type", "string", "description", "Title of the note"), "content",
                Map.of("type", "string", "description", "Content of the note")),
            "required", new String[]{"title", "content"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String title = (String) input.get("title");
          String content = (String) input.get("content");
          notes.put(title, content);
          Map<String, Object> result = new HashMap<>();
          result.put("status", "saved");
          result.put("message", "Note '" + title + "' has been saved.");
          return result;
        });
  }

  /** Creates a new chat session with the given user name. */
  public Session<ConversationState> createSession(String userName) {
    return genkit.createSession(SessionOptions.<ConversationState>builder().store(sessionStore)
        .initialState(new ConversationState(userName)).build());
  }

  /** Loads an existing session by ID. */
  public Session<ConversationState> loadSession(String sessionId) {
    try {
      return genkit
          .loadSession(sessionId, SessionOptions.<ConversationState>builder().store(sessionStore).build())
          .get();
    } catch (Exception e) {
      System.err.println("Failed to load session: " + e.getMessage());
      return null;
    }
  }

  /** Creates a chat instance for a session. */
  @SuppressWarnings("unchecked")
  public Chat<ConversationState> createChat(Session<ConversationState> session, String persona) {
    String systemPrompt = buildSystemPrompt(session, persona);

    return session.chat(ChatOptions.<ConversationState>builder().model("openai/gpt-4o-mini").system(systemPrompt)
        .tools(List.of((Tool<?, ?>) noteTool)).build());
  }

  private String buildSystemPrompt(Session<ConversationState> session, String persona) {
    ConversationState state = session.getState();
    StringBuilder prompt = new StringBuilder();

    // Base persona
    switch (persona.toLowerCase()) {
      case "assistant" :
        prompt.append("You are a helpful, friendly assistant. ");
        break;
      case "tutor" :
        prompt.append("You are a patient and knowledgeable tutor. Explain concepts clearly and encourage"
            + " learning. ");
        break;
      case "creative" :
        prompt.append("You are a creative writing partner. Be imaginative and help with storytelling. ");
        break;
      default :
        prompt.append("You are a helpful assistant. ");
    }

    // Add user context if available
    if (state.getUserName() != null) {
      prompt.append("The user's name is ").append(state.getUserName()).append(". ");
    }

    // Add topic context if set
    if (state.getTopic() != null) {
      prompt.append("The current topic of discussion is: ").append(state.getTopic()).append(". ");
    }

    prompt.append("You can save notes for the user using the saveNote tool when they want to remember"
        + " something important.");

    return prompt.toString();
  }

  /** Sends a message and updates session state. */
  public String chat(Chat<ConversationState> chat, String userMessage) {
    try {
      // Update message count in state
      Session<ConversationState> session = chat.getSession();
      ConversationState state = session.getState();
      state.incrementMessageCount();
      session.updateState(state).join();

      // Send message and get response
      ModelResponse response = chat.send(userMessage);
      return response.getText();
    } catch (Exception e) {
      return "Error: " + e.getMessage();
    }
  }

  /** Displays conversation history. */
  public void showHistory(Chat<ConversationState> chat) {
    System.out.println("\n--- Conversation History ---");
    List<Message> history = chat.getHistory();
    for (Message msg : history) {
      String role = msg.getRole().toString();
      String text = msg.getText();
      if (text.length() > 100) {
        text = text.substring(0, 100) + "...";
      }
      System.out.printf("[%s]: %s%n", role, text);
    }
    System.out.println("--- End History ---\n");
  }

  /** Displays saved notes. */
  public void showNotes() {
    System.out.println("\n--- Saved Notes ---");
    if (notes.isEmpty()) {
      System.out.println("No notes saved yet.");
    } else {
      notes.forEach((title, content) -> System.out.printf("• %s: %s%n", title, content));
    }
    System.out.println("--- End Notes ---\n");
  }

  /** Interactive chat loop. */
  public void runInteractive() {
    Scanner scanner = new Scanner(System.in);

    System.out.println("╔════════════════════════════════════════════════════════════╗");
    System.out.println("║     Genkit Chat Session Demo - Interactive Chat App        ║");
    System.out.println("╚════════════════════════════════════════════════════════════╝");
    System.out.println();

    // Get user name
    System.out.print("What's your name? ");
    String userName = scanner.nextLine().trim();
    if (userName.isEmpty()) {
      userName = "User";
    }

    // Choose persona
    System.out.println("\nChoose a chat persona:");
    System.out.println("  1. Assistant (general help)");
    System.out.println("  2. Tutor (learning & education)");
    System.out.println("  3. Creative (storytelling & ideas)");
    System.out.print("Enter choice (1-3): ");
    String choice = scanner.nextLine().trim();
    String persona = switch (choice) {
      case "2" -> "tutor";
      case "3" -> "creative";
      default -> "assistant";
    };

    // Create session and chat
    Session<ConversationState> session = createSession(userName);
    Chat<ConversationState> chat = createChat(session, persona);

    System.out.println("\n✓ Session created: " + session.getId());
    System.out.println("✓ Persona: " + persona);
    System.out.println("\nCommands:");
    System.out.println("  /history  - Show conversation history");
    System.out.println("  /notes    - Show saved notes");
    System.out.println("  /state    - Show session state");
    System.out.println("  /topic X  - Set conversation topic to X");
    System.out.println("  /quit     - Exit the chat");
    System.out.println("\nStart chatting!\n");

    // Chat loop
    while (true) {
      System.out.print("You: ");
      String input = scanner.nextLine().trim();

      if (input.isEmpty()) {
        continue;
      }

      // Handle commands
      if (input.startsWith("/")) {
        if (input.equals("/quit") || input.equals("/exit")) {
          System.out.println("\nGoodbye, " + userName + "! Session saved.");
          break;
        } else if (input.equals("/history")) {
          showHistory(chat);
          continue;
        } else if (input.equals("/notes")) {
          showNotes();
          continue;
        } else if (input.equals("/state")) {
          System.out.println("\nSession State: " + session.getState());
          continue;
        } else if (input.startsWith("/topic ")) {
          String topic = input.substring(7).trim();
          ConversationState state = session.getState();
          state.setTopic(topic);
          session.updateState(state).join();
          System.out.println("✓ Topic set to: " + topic);
          // Recreate chat with updated system prompt
          chat = createChat(session, persona);
          continue;
        } else {
          System.out.println("Unknown command: " + input);
          continue;
        }
      }

      // Send message
      String response = chat(chat, input);
      System.out.println("\nAssistant: " + response + "\n");
    }

    scanner.close();
  }

  /** Demo mode showing various session features. */
  public void runDemo() {
    System.out.println("╔════════════════════════════════════════════════════════════╗");
    System.out.println("║       Genkit Chat Session Demo - Automated Demo            ║");
    System.out.println("╚════════════════════════════════════════════════════════════╝");
    System.out.println();

    // Demo 1: Basic multi-turn conversation
    System.out.println("=== Demo 1: Multi-turn Conversation ===\n");
    Session<ConversationState> session1 = createSession("Alice");
    Chat<ConversationState> chat1 = createChat(session1, "assistant");

    String[] questions = {"What are the three laws of thermodynamics?",
        "Can you explain the second one in simpler terms?", "How does this relate to entropy?"};

    for (String question : questions) {
      System.out.println("User: " + question);
      String response = chat(chat1, question);
      System.out.println("Assistant: " + truncate(response, 200) + "\n");
    }

    // Demo 2: Session state
    System.out.println("\n=== Demo 2: Session State ===\n");
    System.out.println("Session ID: " + session1.getId());
    System.out.println("State: " + session1.getState());

    // Demo 3: Save and load session
    System.out.println("\n=== Demo 3: Session Persistence ===\n");
    String sessionId = session1.getId();
    System.out.println("Saving session: " + sessionId);

    // Load the session
    Session<ConversationState> loadedSession = loadSession(sessionId);
    if (loadedSession != null) {
      System.out.println("✓ Session loaded successfully!");
      System.out.println("  Messages in history: " + loadedSession.getMessages().size());
      System.out.println("  State: " + loadedSession.getState());

      // Continue the conversation
      Chat<ConversationState> continuedChat = createChat(loadedSession, "assistant");
      System.out.println("\nContinuing conversation...");
      System.out.println("User: Can you summarize what we discussed?");
      String summary = chat(continuedChat, "Can you summarize what we discussed?");
      System.out.println("Assistant: " + truncate(summary, 300));
    }

    // Demo 4: Using tools
    System.out.println("\n\n=== Demo 4: Using Tools (Note Taking) ===\n");
    Session<ConversationState> session2 = createSession("Bob");
    Chat<ConversationState> chat2 = createChat(session2, "assistant");

    System.out.println("User: Please save a note titled 'Meeting' with content 'Review Q4 goals'");
    String noteResponse = chat(chat2, "Please save a note titled 'Meeting' with content 'Review Q4 goals'");
    System.out.println("Assistant: " + noteResponse);
    showNotes();

    System.out.println("\n=== Demo Complete ===");
  }

  private String truncate(String text, int maxLength) {
    if (text == null) {
      return "";
    }
    if (text.length() <= maxLength) {
      return text;
    }
    return text.substring(0, maxLength) + "...";
  }

  public static void main(String[] args) {
    ChatSessionApp app = new ChatSessionApp();

    // Check for demo mode flag
    boolean demoMode = args.length > 0 && args[0].equals("--demo");

    if (demoMode) {
      app.runDemo();
    } else {
      app.runInteractive();
    }
  }
}

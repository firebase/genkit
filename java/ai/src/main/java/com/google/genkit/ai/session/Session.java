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

package com.google.genkit.ai.session;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Supplier;

import com.google.genkit.ai.Agent;
import com.google.genkit.ai.Message;
import com.google.genkit.core.Registry;

/**
 * Session represents a stateful chat session that persists conversation history
 * and custom state across multiple interactions.
 *
 * <p>
 * Sessions provide:
 * <ul>
 * <li>Persistent conversation threads</li>
 * <li>Custom state management</li>
 * <li>Multiple named chat threads within a session</li>
 * <li>Automatic history management</li>
 * </ul>
 *
 * <p>
 * Example usage:
 * 
 * <pre>{@code
 * // Create a session with initial state
 * Session<MyState> session = genkit
 * 		.createSession(SessionOptions.<MyState>builder().initialState(new MyState("John")).build());
 *
 * // Create a chat and interact
 * Chat chat = session.chat();
 * ModelResponse response = chat.send("Hello!");
 *
 * // Access session state
 * MyState state = session.getState();
 * }</pre>
 *
 * @param <S>
 *            the type of the custom session state
 */
public class Session<S> {

  /** Default thread name for chat conversations. */
  public static final String DEFAULT_THREAD = "main";

  private final String id;
  private SessionData<S> sessionData;
  private final SessionStore<S> store;
  private final Registry registry;
  private final Supplier<Chat<S>> chatFactory;
  private final Map<String, Agent> agentRegistry;

  /**
   * Creates a new Session.
   *
   * @param registry
   *            the Genkit registry
   * @param store
   *            the session store
   * @param sessionData
   *            the initial session data
   * @param chatFactory
   *            factory for creating Chat instances
   * @param agentRegistry
   *            the agent registry for multi-agent handoffs (may be null)
   */
  Session(Registry registry, SessionStore<S> store, SessionData<S> sessionData, Supplier<Chat<S>> chatFactory,
      Map<String, Agent> agentRegistry) {
    this.registry = registry;
    this.store = store;
    this.sessionData = sessionData;
    this.id = sessionData.getId();
    this.chatFactory = chatFactory;
    this.agentRegistry = agentRegistry;
  }

  /**
   * Gets the session ID.
   *
   * @return the unique session identifier
   */
  public String getId() {
    return id;
  }

  /**
   * Gets the current session state.
   *
   * @return the session state, or null if not set
   */
  public S getState() {
    return sessionData.getState();
  }

  /**
   * Updates the session state and persists it.
   *
   * @param state
   *            the new state
   * @return a CompletableFuture that completes when the state is saved
   */
  public CompletableFuture<Void> updateState(S state) {
    sessionData.setState(state);
    return store.save(id, sessionData);
  }

  /**
   * Gets the message history for a thread.
   *
   * @param threadName
   *            the thread name
   * @return the list of messages in the thread
   */
  public List<Message> getMessages(String threadName) {
    List<Message> messages = sessionData.getThread(threadName);
    return messages != null ? new ArrayList<>(messages) : new ArrayList<>();
  }

  /**
   * Gets the message history for the default thread.
   *
   * @return the list of messages
   */
  public List<Message> getMessages() {
    return getMessages(DEFAULT_THREAD);
  }

  /**
   * Updates the messages for a thread and persists them.
   *
   * @param threadName
   *            the thread name
   * @param messages
   *            the messages to save
   * @return a CompletableFuture that completes when saved
   */
  public CompletableFuture<Void> updateMessages(String threadName, List<Message> messages) {
    sessionData.setThread(threadName, messages);
    return store.save(id, sessionData);
  }

  /**
   * Creates a new Chat instance for the default thread.
   *
   * @return a new Chat instance
   */
  public Chat<S> chat() {
    return chat(DEFAULT_THREAD, ChatOptions.<S>builder().build());
  }

  /**
   * Creates a new Chat instance with options.
   *
   * @param options
   *            the chat options
   * @return a new Chat instance
   */
  public Chat<S> chat(ChatOptions<S> options) {
    return chat(DEFAULT_THREAD, options);
  }

  /**
   * Creates a new Chat instance for a specific thread.
   *
   * @param threadName
   *            the thread name
   * @return a new Chat instance
   */
  public Chat<S> chat(String threadName) {
    return chat(threadName, ChatOptions.<S>builder().build());
  }

  /**
   * Creates a new Chat instance for a specific thread with options.
   *
   * @param threadName
   *            the thread name
   * @param options
   *            the chat options
   * @return a new Chat instance
   */
  public Chat<S> chat(String threadName, ChatOptions<S> options) {
    return new Chat<>(this, threadName, options, registry, agentRegistry);
  }

  /**
   * Gets the session store.
   *
   * @return the session store
   */
  public SessionStore<S> getStore() {
    return store;
  }

  /**
   * Gets the registry.
   *
   * @return the registry
   */
  public Registry getRegistry() {
    return registry;
  }

  /**
   * Gets the agent registry for multi-agent handoffs.
   *
   * @return the agent registry, or null if not set
   */
  public Map<String, Agent> getAgentRegistry() {
    return agentRegistry;
  }

  /**
   * Gets the session data.
   *
   * @return the session data
   */
  public SessionData<S> getSessionData() {
    return sessionData;
  }

  /**
   * Serializes the session to JSON-compatible data.
   *
   * @return the session data
   */
  public SessionData<S> toJSON() {
    return sessionData;
  }

  /**
   * Creates a new Session with a generated ID.
   *
   * @param <S>
   *            the state type
   * @param registry
   *            the Genkit registry
   * @param options
   *            the session options
   * @return a new Session
   */
  public static <S> Session<S> create(Registry registry, SessionOptions<S> options) {
    return create(registry, options, null);
  }

  /**
   * Creates a new Session with a generated ID and agent registry.
   *
   * @param <S>
   *            the state type
   * @param registry
   *            the Genkit registry
   * @param options
   *            the session options
   * @param agentRegistry
   *            the agent registry for multi-agent handoffs (may be null)
   * @return a new Session
   */
  public static <S> Session<S> create(Registry registry, SessionOptions<S> options,
      Map<String, Agent> agentRegistry) {
    String sessionId = options.getSessionId() != null ? options.getSessionId() : UUID.randomUUID().toString();

    SessionStore<S> store = options.getStore() != null ? options.getStore() : new InMemorySessionStore<>();

    SessionData<S> data = SessionData.<S>builder().id(sessionId).state(options.getInitialState()).build();

    // Save initial session data
    store.save(sessionId, data).join();

    return new Session<>(registry, store, data, null, agentRegistry);
  }

  /**
   * Loads an existing session from a store.
   *
   * @param <S>
   *            the state type
   * @param registry
   *            the Genkit registry
   * @param sessionId
   *            the session ID to load
   * @param options
   *            the session options (must include store)
   * @return a CompletableFuture containing the loaded session, or null if not
   *         found
   */
  public static <S> CompletableFuture<Session<S>> load(Registry registry, String sessionId,
      SessionOptions<S> options) {
    return load(registry, sessionId, options, null);
  }

  /**
   * Loads an existing session from a store with agent registry.
   *
   * @param <S>
   *            the state type
   * @param registry
   *            the Genkit registry
   * @param sessionId
   *            the session ID to load
   * @param options
   *            the session options (must include store)
   * @param agentRegistry
   *            the agent registry for multi-agent handoffs (may be null)
   * @return a CompletableFuture containing the loaded session, or null if not
   *         found
   */
  public static <S> CompletableFuture<Session<S>> load(Registry registry, String sessionId, SessionOptions<S> options,
      Map<String, Agent> agentRegistry) {
    SessionStore<S> store = options.getStore() != null ? options.getStore() : new InMemorySessionStore<>();

    return store.get(sessionId).thenApply(data -> {
      if (data == null) {
        return null;
      }
      return new Session<>(registry, store, data, null, agentRegistry);
    });
  }
}

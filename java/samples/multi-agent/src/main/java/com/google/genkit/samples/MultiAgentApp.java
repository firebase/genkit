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

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Scanner;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.Agent;
import com.google.genkit.ai.AgentConfig;
import com.google.genkit.ai.GenerationConfig;
import com.google.genkit.ai.Tool;
import com.google.genkit.ai.session.Chat;
import com.google.genkit.ai.session.ChatOptions;
import com.google.genkit.ai.session.InMemorySessionStore;
import com.google.genkit.ai.session.Session;
import com.google.genkit.ai.session.SessionOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;

/**
 * Multi-Agent Customer Service Application.
 *
 * <p>
 * This sample demonstrates the multi-agent pattern where:
 * <ul>
 * <li>A triage agent routes requests to specialized agents</li>
 * <li>Specialized agents handle specific domains (reservations, menu,
 * etc.)</li>
 * <li>Agents can be used as tools for delegation</li>
 * </ul>
 *
 * <p>
 * To run:
 * <ol>
 * <li>Set the OPENAI_API_KEY environment variable</li>
 * <li>Run: mvn exec:java -pl samples/multi-agent</li>
 * </ol>
 */
public class MultiAgentApp {

  /** Customer state for tracking context. */
  public static class CustomerState {
    private String customerId;
    private String currentAgent;
    private List<String> reservations = new ArrayList<>();
    private List<String> orders = new ArrayList<>();

    public CustomerState() {
      this.customerId = "customer-" + System.currentTimeMillis();
      this.currentAgent = "triage";
    }

    public String getCustomerId() {
      return customerId;
    }

    public String getCurrentAgent() {
      return currentAgent;
    }

    public void setCurrentAgent(String agent) {
      this.currentAgent = agent;
    }

    public List<String> getReservations() {
      return reservations;
    }

    public void addReservation(String reservation) {
      this.reservations.add(reservation);
    }

    public List<String> getOrders() {
      return orders;
    }

    public void addOrder(String order) {
      this.orders.add(order);
    }

    @Override
    public String toString() {
      return String.format("Customer: %s, Agent: %s, Reservations: %d, Orders: %d", customerId, currentAgent,
          reservations.size(), orders.size());
    }
  }

  private final Genkit genkit;
  private final InMemorySessionStore<CustomerState> sessionStore;

  // Agents
  private Agent triageAgent;
  private Agent reservationAgent;
  private Agent menuAgent;
  private Agent orderAgent;

  // Tools
  private Tool<?, ?> makeReservationTool;
  private Tool<?, ?> cancelReservationTool;
  private Tool<?, ?> getMenuTool;
  private Tool<?, ?> placeOrderTool;

  public MultiAgentApp() {
    // Initialize Genkit
    this.genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3101).build())
        .plugin(OpenAIPlugin.create()).build();

    this.sessionStore = new InMemorySessionStore<>();

    // Initialize tools and agents
    initializeTools();
    initializeAgents();
  }

  @SuppressWarnings("unchecked")
  private void initializeTools() {
    // Reservation Tool
    makeReservationTool = genkit.defineTool("makeReservation", "Makes a restaurant reservation for the customer",
        Map.of("type", "object", "properties",
            Map.of("date", Map.of("type", "string", "description", "Date in YYYY-MM-DD format"), "time",
                Map.of("type", "string", "description", "Time in HH:MM format"), "partySize",
                Map.of("type", "integer", "description", "Number of guests")),
            "required", new String[]{"date", "time", "partySize"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String date = (String) input.get("date");
          String time = (String) input.get("time");
          Integer partySize = (Integer) input.get("partySize");
          String confirmationId = "RES-" + System.currentTimeMillis() % 10000;

          Map<String, Object> result = new HashMap<>();
          result.put("status", "confirmed");
          result.put("confirmationId", confirmationId);
          result.put("date", date);
          result.put("time", time);
          result.put("partySize", partySize);
          result.put("message",
              String.format("Reservation confirmed for %d guests on %s at %s. Confirmation: %s",
                  partySize, date, time, confirmationId));
          return result;
        });

    // Cancel Reservation Tool
    cancelReservationTool = genkit.defineTool("cancelReservation", "Cancels an existing reservation",
        Map.of("type", "object", "properties",
            Map.of("confirmationId",
                Map.of("type", "string", "description", "The reservation confirmation ID")),
            "required", new String[]{"confirmationId"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String confirmationId = (String) input.get("confirmationId");
          Map<String, Object> result = new HashMap<>();
          result.put("status", "cancelled");
          result.put("confirmationId", confirmationId);
          result.put("message", "Reservation " + confirmationId + " has been cancelled.");
          return result;
        });

    // Menu Tool
    getMenuTool = genkit.defineTool("getMenu", "Gets the current restaurant menu",
        Map.of("type", "object", "properties",
            Map.of("category",
                Map.of("type", "string", "description",
                    "Menu category: appetizers, mains, desserts, drinks, or all", "enum",
                    new String[]{"appetizers", "mains", "desserts", "drinks", "all"}))),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String category = input.get("category") != null ? (String) input.get("category") : "all";
          Map<String, Object> menu = new HashMap<>();

          if (category.equals("all") || category.equals("appetizers")) {
            menu.put("appetizers", List.of(
                Map.of("name", "Bruschetta", "price", 8.99, "description",
                    "Toasted bread with tomatoes"),
                Map.of("name", "Calamari", "price", 12.99, "description", "Fried squid rings")));
          }
          if (category.equals("all") || category.equals("mains")) {
            menu.put("mains", List.of(
                Map.of("name", "Grilled Salmon", "price", 24.99, "description",
                    "Atlantic salmon with herbs"),
                Map.of("name", "Ribeye Steak", "price", 32.99, "description", "12oz prime ribeye"),
                Map.of("name", "Pasta Primavera", "price", 18.99, "description",
                    "Seasonal vegetables")));
          }
          if (category.equals("all") || category.equals("desserts")) {
            menu.put("desserts",
                List.of(Map.of("name", "Tiramisu", "price", 9.99, "description",
                    "Classic Italian dessert"),
                    Map.of("name", "Cheesecake", "price", 8.99, "description", "NY style")));
          }
          if (category.equals("all") || category.equals("drinks")) {
            menu.put("drinks",
                List.of(Map.of("name", "House Wine", "price", 8.99, "description", "Red or white"),
                    Map.of("name", "Craft Beer", "price", 6.99, "description", "Local selection")));
          }

          return menu;
        });

    // Order Tool
    placeOrderTool = genkit.defineTool("placeOrder", "Places a food order for pickup or delivery",
        Map.of("type", "object", "properties",
            Map.of("items",
                Map.of("type", "array", "items", Map.of("type", "string"), "description",
                    "List of menu item names to order"),
                "orderType",
                Map.of("type", "string", "description", "pickup or delivery", "enum",
                    new String[]{"pickup", "delivery"})),
            "required", new String[]{"items", "orderType"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          @SuppressWarnings("unchecked")
          List<String> items = (List<String>) input.get("items");
          String orderType = (String) input.get("orderType");
          String orderId = "ORD-" + System.currentTimeMillis() % 10000;

          Map<String, Object> result = new HashMap<>();
          result.put("status", "confirmed");
          result.put("orderId", orderId);
          result.put("items", items);
          result.put("orderType", orderType);
          result.put("estimatedTime", orderType.equals("pickup") ? "20 minutes" : "45 minutes");
          result.put("message",
              String.format("Order %s placed for %s. Items: %s. Ready in %s.", orderId, orderType,
                  String.join(", ", items),
                  orderType.equals("pickup") ? "20 minutes" : "45 minutes"));
          return result;
        });
  }

  @SuppressWarnings("unchecked")
  private void initializeAgents() {
    // Reservation Agent - handles booking and cancellation
    // Note: genkit.defineAgent automatically registers the agent
    reservationAgent = genkit.defineAgent(AgentConfig.builder().name("reservationAgent")
        .description("Handles restaurant reservations. Transfer to this agent when the customer "
            + "wants to make, modify, or cancel a reservation.")
        .system("You are a reservation specialist for an upscale restaurant. "
            + "Help customers make, modify, or cancel reservations. "
            + "Always confirm the date, time, and party size before making a reservation. "
            + "Be professional and courteous.")
        .model("openai/gpt-4o-mini").tools(List.of(makeReservationTool, cancelReservationTool))
        .config(GenerationConfig.builder().temperature(0.3).build()).build());

    // Menu Agent - provides menu information
    menuAgent = genkit.defineAgent(AgentConfig.builder().name("menuAgent")
        .description("Provides menu information. Transfer to this agent when the customer "
            + "wants to know about menu items, prices, or recommendations.")
        .system("You are a menu expert at an upscale restaurant. "
            + "Help customers explore the menu, understand dishes, and get recommendations. "
            + "Use the getMenu tool to retrieve current menu items. "
            + "Be knowledgeable about ingredients and preparation methods.")
        .model("openai/gpt-4o-mini").tools(List.of(getMenuTool))
        .config(GenerationConfig.builder().temperature(0.5).build()).build());

    // Order Agent - handles food orders
    orderAgent = genkit.defineAgent(AgentConfig.builder().name("orderAgent")
        .description("Handles food orders for pickup or delivery. Transfer to this agent when "
            + "the customer wants to place an order.")
        .system("You are an order specialist for a restaurant. "
            + "Help customers place orders for pickup or delivery. "
            + "Confirm all items before placing the order. " + "Provide accurate time estimates.")
        .model("openai/gpt-4o-mini").tools(List.of(placeOrderTool, getMenuTool))
        .config(GenerationConfig.builder().temperature(0.3).build()).build());

    // Triage Agent - routes to specialized agents
    triageAgent = genkit.defineAgent(AgentConfig.builder().name("triageAgent")
        .description("Main customer service agent that routes requests to specialists")
        .system("You are the main customer service agent for The Golden Fork restaurant. "
            + "Your job is to understand what the customer needs and transfer them to the right specialist.\n\n"
            + "IMPORTANT: To transfer to another agent, you MUST call the appropriate agent tool. "
            + "Do NOT just say you are transferring - you must actually invoke the tool:\n"
            + "- reservationAgent: for reservations (booking, canceling, modifying)\n"
            + "- menuAgent: for menu questions, recommendations, or dietary info\n"
            + "- orderAgent: for placing orders (pickup or delivery)\n\n"
            + "When a customer needs help with a specific task, call the corresponding agent tool immediately. "
            + "You can handle general greetings and questions, but for specific tasks, always use the tools.")
        .model("openai/gpt-4o-mini")
        .agents(List.of(reservationAgent.getConfig(), menuAgent.getConfig(), orderAgent.getConfig()))
        .config(GenerationConfig.builder().temperature(0.7).build()).build());
  }

  /** Creates a chat session with the triage agent. */
  @SuppressWarnings("unchecked")
  public Chat<CustomerState> createChat() {
    Session<CustomerState> session = genkit.createSession(
        SessionOptions.<CustomerState>builder().store(sessionStore).initialState(new CustomerState()).build());

    // Get all tools including sub-agents as tools - Genkit handles the registry
    List<Tool<?, ?>> allTools = genkit.getAllToolsForAgent(triageAgent);

    // Agent registry is automatically available from the session - no need to pass
    // explicitly
    return session.chat(ChatOptions.<CustomerState>builder().model("openai/gpt-4o-mini")
        .system(triageAgent.getSystem()).tools(allTools).build());
  }

  /** Interactive chat loop. */
  public void runInteractive() {
    Scanner scanner = new Scanner(System.in);

    System.out.println("╔════════════════════════════════════════════════════════════════╗");
    System.out.println("║      The Golden Fork Restaurant - Multi-Agent Customer Service ║");
    System.out.println("╚════════════════════════════════════════════════════════════════╝");
    System.out.println();
    System.out.println("Available agents:");
    System.out.println("  • Triage Agent - Routes your requests");
    System.out.println("  • Reservation Agent - Handles bookings");
    System.out.println("  • Menu Agent - Menu information and recommendations");
    System.out.println("  • Order Agent - Pickup and delivery orders");
    System.out.println();
    System.out.println("Commands:");
    System.out.println("  /status  - Show current state");
    System.out.println("  /quit    - Exit");
    System.out.println();
    System.out.println("How can we help you today?\n");

    Chat<CustomerState> chat = createChat();

    while (true) {
      System.out.print("You: ");
      String input = scanner.nextLine().trim();

      if (input.isEmpty())
        continue;

      if (input.equals("/quit") || input.equals("/exit")) {
        System.out.println("\nThank you for visiting The Golden Fork!");
        break;
      }

      if (input.equals("/status")) {
        String currentAgent = chat.getCurrentAgentName();
        System.out.println("\nState: " + chat.getSession().getState());
        System.out
            .println("Current Agent: " + (currentAgent != null ? currentAgent : "triage (default)") + "\n");
        continue;
      }

      try {
        String response = chat.send(input).getText();
        System.out.println("\nAssistant: " + response + "\n");
      } catch (Exception e) {
        System.out.println("\nError: " + e.getMessage() + "\n");
      }
    }

    scanner.close();
  }

  /** Demo mode. */
  public void runDemo() {
    System.out.println("╔════════════════════════════════════════════════════════════════╗");
    System.out.println("║      Multi-Agent Demo - Restaurant Customer Service            ║");
    System.out.println("╚════════════════════════════════════════════════════════════════╝");
    System.out.println();

    Chat<CustomerState> chat = createChat();

    // Demo conversation
    String[] messages = {"Hi, I'd like to make a reservation for this weekend", "Saturday at 7pm for 4 people",
        "Thanks! Also, what's on your dessert menu?",
        "I'd like to place a pickup order for the Tiramisu and Cheesecake"};

    for (String message : messages) {
      System.out.println("Customer: " + message);
      try {
        String response = chat.send(message).getText();
        System.out.println("\nAssistant: " + truncate(response, 300) + "\n");
        Thread.sleep(1000); // Pause for readability
      } catch (Exception e) {
        System.out.println("Error: " + e.getMessage());
      }
    }

    System.out.println("\n=== Demo Complete ===");
    System.out.println("Final state: " + chat.getSession().getState());
  }

  private String truncate(String text, int maxLength) {
    if (text == null || text.length() <= maxLength)
      return text;
    return text.substring(0, maxLength) + "...";
  }

  public static void main(String[] args) {
    MultiAgentApp app = new MultiAgentApp();

    boolean demoMode = args.length > 0 && args[0].equals("--demo");

    if (demoMode) {
      app.runDemo();
    } else {
      app.runInteractive();
    }
  }
}

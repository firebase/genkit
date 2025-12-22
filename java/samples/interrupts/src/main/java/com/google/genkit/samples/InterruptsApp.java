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
import java.util.List;
import java.util.Map;
import java.util.Scanner;

import com.google.genkit.Genkit;
import com.google.genkit.GenkitOptions;
import com.google.genkit.ai.GenerateOptions;
import com.google.genkit.ai.InterruptConfig;
import com.google.genkit.ai.InterruptRequest;
import com.google.genkit.ai.ModelResponse;
import com.google.genkit.ai.Part;
import com.google.genkit.ai.ResumeOptions;
import com.google.genkit.ai.Tool;
import com.google.genkit.ai.ToolResponse;
import com.google.genkit.ai.session.Chat;
import com.google.genkit.ai.session.ChatOptions;
import com.google.genkit.ai.session.InMemorySessionStore;
import com.google.genkit.ai.session.Session;
import com.google.genkit.ai.session.SessionOptions;
import com.google.genkit.plugins.openai.OpenAIPlugin;
import com.google.genkit.prompt.ExecutablePrompt;

/**
 * Human-in-the-Loop Application using Interrupts.
 *
 * <p>
 * This sample demonstrates the interrupt pattern for human-in-the-loop
 * scenarios:
 * <ul>
 * <li>Tools that pause execution to request user confirmation</li>
 * <li>Handling interrupt requests and resuming with user input</li>
 * <li>Sensitive operations that require explicit approval</li>
 * </ul>
 *
 * <p>
 * To run:
 * <ol>
 * <li>Set the OPENAI_API_KEY environment variable</li>
 * <li>Run: mvn exec:java -pl samples/interrupts</li>
 * </ol>
 */
public class InterruptsApp {

  /** Confirmation input structure. */
  public static class ConfirmationInput {
    private String action;
    private String details;
    private double amount;

    public ConfirmationInput() {
    }

    public String getAction() {
      return action;
    }
    public void setAction(String action) {
      this.action = action;
    }
    public String getDetails() {
      return details;
    }
    public void setDetails(String details) {
      this.details = details;
    }
    public double getAmount() {
      return amount;
    }
    public void setAmount(double amount) {
      this.amount = amount;
    }
  }

  /** Transfer request for the interrupt tool input. */
  public static class TransferRequest {
    private String recipient;
    private double amount;
    private String reason;

    public TransferRequest() {
    }

    public String getRecipient() {
      return recipient;
    }
    public void setRecipient(String recipient) {
      this.recipient = recipient;
    }
    public double getAmount() {
      return amount;
    }
    public void setAmount(double amount) {
      this.amount = amount;
    }
    public String getReason() {
      return reason;
    }
    public void setReason(String reason) {
      this.reason = reason;
    }
  }

  /** Confirmation output structure. */
  public static class ConfirmationOutput {
    private boolean confirmed;
    private String reason;

    public ConfirmationOutput() {
    }
    public ConfirmationOutput(boolean confirmed, String reason) {
      this.confirmed = confirmed;
      this.reason = reason;
    }

    public boolean isConfirmed() {
      return confirmed;
    }
    public void setConfirmed(boolean confirmed) {
      this.confirmed = confirmed;
    }
    public String getReason() {
      return reason;
    }
    public void setReason(String reason) {
      this.reason = reason;
    }
  }

  /** Bank account state. */
  public static class AccountState {
    private String accountId;
    private double balance;
    private List<String> transactions = new ArrayList<>();

    public AccountState() {
      this.accountId = "ACC-" + System.currentTimeMillis() % 10000;
      this.balance = 5000.00; // Starting balance
    }

    public String getAccountId() {
      return accountId;
    }
    public double getBalance() {
      return balance;
    }

    public void addTransaction(String transaction, double amount) {
      this.balance += amount;
      this.transactions.add(transaction);
    }

    public List<String> getTransactions() {
      return transactions;
    }

    @Override
    public String toString() {
      return String.format("Account: %s, Balance: $%.2f, Transactions: %d", accountId, balance,
          transactions.size());
    }
  }

  /** Banking request input for the prompt. */
  public static class BankingInput {
    private String request;

    public BankingInput() {
    }

    public BankingInput(String request) {
      this.request = request;
    }

    public String getRequest() {
      return request;
    }

    public void setRequest(String request) {
      this.request = request;
    }
  }

  private final Genkit genkit;
  private final InMemorySessionStore<AccountState> sessionStore;
  private final Scanner scanner;

  // Tools
  private Tool<?, ?> getBalanceTool;
  private Tool<?, ?> transferMoneyTool;
  private Tool<?, ?> confirmTransferTool;

  public InterruptsApp() {
    this.genkit = Genkit.builder().options(GenkitOptions.builder().devMode(true).reflectionPort(3102).build())
        .plugin(OpenAIPlugin.create()).build();

    this.sessionStore = new InMemorySessionStore<>();
    this.scanner = new Scanner(System.in);

    initializeTools();
  }

  @SuppressWarnings("unchecked")
  private void initializeTools() {
    // Get Balance Tool - no confirmation needed
    getBalanceTool = genkit.defineTool("getBalance", "Gets the current account balance",
        Map.of("type", "object", "properties", Map.of()), (Class<Map<String, Object>>) (Class<?>) Map.class,
        (ctx, input) -> {
          // In a real app, we'd get this from session context
          return Map.of("balance", 5000.00, "currency", "USD");
        });

    // Use defineInterrupt to create an interrupt tool that pauses for confirmation.
    // This is the preferred way to create interrupt tools - it automatically
    // handles
    // throwing ToolInterruptException with the proper metadata.
    confirmTransferTool = genkit
        .defineInterrupt(InterruptConfig.<TransferRequest, ConfirmationOutput>builder().name("confirmTransfer")
            .description("Request user confirmation before executing a money transfer. "
                + "ALWAYS use this tool before transferring money.")
            .inputType(TransferRequest.class).outputType(ConfirmationOutput.class)
            .inputSchema(Map.of("type", "object", "properties",
                Map.of("recipient", Map.of("type", "string", "description", "Who to transfer to"),
                    "amount", Map.of("type", "number", "description", "Amount to transfer"),
                    "reason", Map.of("type", "string", "description", "Reason for transfer")),
                "required", new String[]{"recipient", "amount"}))
            // requestMetadata extracts info from input for the interrupt request
            .requestMetadata(input -> Map.of("type", "transfer_confirmation", "recipient",
                input.getRecipient(), "amount", input.getAmount(), "reason",
                input.getReason() != null ? input.getReason() : ""))
            .build());

    // Transfer Money Tool - executes after confirmation
    transferMoneyTool = genkit.defineTool("executeTransfer",
        "Executes a confirmed money transfer. Only call this after confirmation.",
        Map.of("type", "object", "properties",
            Map.of("recipient", Map.of("type", "string", "description", "Transfer recipient"), "amount",
                Map.of("type", "number", "description", "Amount to transfer"), "confirmationCode",
                Map.of("type", "string", "description", "Confirmation code from user")),
            "required", new String[]{"recipient", "amount", "confirmationCode"}),
        (Class<Map<String, Object>>) (Class<?>) Map.class, (ctx, input) -> {
          String recipient = (String) input.get("recipient");
          double amount = ((Number) input.get("amount")).doubleValue();
          String transactionId = "TXN-" + System.currentTimeMillis() % 100000;

          return Map.of("status", "success", "transactionId", transactionId, "recipient", recipient, "amount",
              amount, "message", String.format("Successfully transferred $%.2f to %s. Transaction ID: %s",
                  amount, recipient, transactionId));
        });
  }

  /** Creates a chat session. */
  @SuppressWarnings("unchecked")
  public Chat<AccountState> createChat() {
    Session<AccountState> session = genkit.createSession(
        SessionOptions.<AccountState>builder().store(sessionStore).initialState(new AccountState()).build());

    String systemPrompt = "You are a helpful banking assistant for SecureBank. "
        + "You can help customers check their balance and transfer money. "
        + "IMPORTANT: For any money transfer, you MUST first use the confirmTransfer tool "
        + "to get user confirmation. Never execute a transfer without confirmation. "
        + "After the user confirms, use the executeTransfer tool with their confirmation code.";

    return session.chat(ChatOptions.<AccountState>builder().model("openai/gpt-4o-mini").system(systemPrompt)
        .tools(List.of(getBalanceTool, confirmTransferTool, transferMoneyTool)).build());
  }

  /** Handles an interrupt by prompting the user. */
  private ConfirmationOutput handleInterrupt(InterruptRequest interrupt) {
    Map<String, Object> metadata = interrupt.getMetadata();

    System.out.println("\n╔═══════════════════════════════════════════════════════════╗");
    System.out.println("║           ⚠️  CONFIRMATION REQUIRED ⚠️                      ║");
    System.out.println("╠═══════════════════════════════════════════════════════════╣");
    System.out.printf("║  Transfer: $%.2f to %s%n", metadata.get("amount"), metadata.get("recipient"));
    if (metadata.get("reason") != null) {
      System.out.printf("║  Reason: %s%n", metadata.get("reason"));
    }
    System.out.println("╠═══════════════════════════════════════════════════════════╣");
    System.out.println("║  Type 'yes' to confirm or 'no' to cancel                  ║");
    System.out.println("╚═══════════════════════════════════════════════════════════╝");
    System.out.print("\nYour decision: ");

    String response = scanner.nextLine().trim().toLowerCase();
    boolean confirmed = response.equals("yes") || response.equals("y");

    if (confirmed) {
      System.out.println("✓ Transfer confirmed");
      return new ConfirmationOutput(true, "User confirmed with code: CONF-" + System.currentTimeMillis() % 10000);
    } else {
      System.out.println("✗ Transfer cancelled");
      return new ConfirmationOutput(false, "User declined the transfer");
    }
  }

  /** Sends a message and handles any interrupts. */
  public String sendWithInterruptHandling(Chat<AccountState> chat, String message) {
    try {
      ModelResponse response = chat.send(message);

      // Check for pending interrupts
      if (chat.hasPendingInterrupts()) {
        List<InterruptRequest> interrupts = chat.getPendingInterrupts();

        for (InterruptRequest interrupt : interrupts) {
          // Handle the interrupt (get user confirmation)
          ConfirmationOutput userResponse = handleInterrupt(interrupt);

          // Create resume options with the user's response
          ToolResponse toolResponse = interrupt.respond(userResponse);
          ResumeOptions resume = ResumeOptions.builder().respond(List.of(toolResponse)).build();

          // Resume the conversation with the user's response
          response = chat.send(
              userResponse.isConfirmed()
                  ? "User confirmed. Proceed with the transfer."
                  : "User declined. Cancel the transfer.",
              Chat.SendOptions.builder().resumeOptions(resume).build());
        }
      }

      return response.getText();
    } catch (Exception e) {
      return "Error: " + e.getMessage();
    }
  }

  /** Interactive chat loop. */
  public void runInteractive() {
    System.out.println("╔════════════════════════════════════════════════════════════════╗");
    System.out.println("║      SecureBank - Human-in-the-Loop Banking Assistant          ║");
    System.out.println("╚════════════════════════════════════════════════════════════════╝");
    System.out.println();
    System.out.println("This demo shows the interrupt pattern for sensitive operations.");
    System.out.println("Money transfers require explicit confirmation before execution.");
    System.out.println();
    System.out.println("Try saying:");
    System.out.println("  • 'What's my balance?'");
    System.out.println("  • 'Transfer $100 to John for lunch'");
    System.out.println("  • 'Send $500 to Alice'");
    System.out.println();
    System.out.println("Commands: /status, /quit\n");

    Chat<AccountState> chat = createChat();

    while (true) {
      System.out.print("You: ");
      String input = scanner.nextLine().trim();

      if (input.isEmpty())
        continue;

      if (input.equals("/quit") || input.equals("/exit")) {
        System.out.println("\nThank you for banking with SecureBank!");
        break;
      }

      if (input.equals("/status")) {
        System.out.println("\n" + chat.getSession().getState() + "\n");
        continue;
      }

      String response = sendWithInterruptHandling(chat, input);
      System.out.println("\nAssistant: " + response + "\n");
    }
  }

  /** Demo mode. */
  public void runDemo() {
    System.out.println("╔════════════════════════════════════════════════════════════════╗");
    System.out.println("║      Interrupts Demo - Human-in-the-Loop Pattern               ║");
    System.out.println("╚════════════════════════════════════════════════════════════════╝");
    System.out.println();
    System.out.println("This demo shows how interrupts work for human-in-the-loop scenarios.");
    System.out.println("Watch how the system pauses for confirmation on sensitive operations.\n");

    Chat<AccountState> chat = createChat();

    // Demo 1: Check balance (no interrupt)
    System.out.println("=== Demo 1: Simple Query (No Interrupt) ===\n");
    System.out.println("Customer: What's my current balance?");
    String response1 = sendWithInterruptHandling(chat, "What's my current balance?");
    System.out.println("Assistant: " + response1 + "\n");

    // Demo 2: Transfer money (triggers interrupt)
    System.out.println("\n=== Demo 2: Transfer Request (Triggers Interrupt) ===\n");
    System.out.println("Customer: Transfer $250 to John Smith for the concert tickets");
    System.out.println("\n[The system will now request confirmation...]\n");

    // For demo, we'll use a mock confirmation
    String response2 = sendWithInterruptHandling(chat, "Transfer $250 to John Smith for the concert tickets");
    System.out.println("\nAssistant: " + response2);

    System.out.println("\n=== Demo Complete ===");
    System.out.println("Final state: " + chat.getSession().getState());
  }

  /**
   * Demo using generate() directly with interrupts (without Chat).
   * 
   * <p>
   * This shows how to use interrupts at the lower level generate() API, which is
   * useful when you don't need session management.
   */
  public void runGenerateDemo() {
    System.out.println("╔════════════════════════════════════════════════════════════════╗");
    System.out.println("║    Interrupts with generate() - Low-Level API Demo             ║");
    System.out.println("╚════════════════════════════════════════════════════════════════╝");
    System.out.println();
    System.out.println("This demo shows how to use interrupts with the generate() method.");
    System.out.println("This is useful when you don't need Chat's session management.\n");

    String model = "openai/gpt-4o-mini";

    // Create a simple confirm transfer interrupt tool
    @SuppressWarnings("unchecked")
    Tool<TransferRequest, ConfirmationOutput> confirmTool = (Tool<TransferRequest, ConfirmationOutput>) confirmTransferTool;

    // Initial request - transfer money
    System.out.println("=== Step 1: Initial Generate Request ===\n");
    System.out.println("Prompt: Transfer $150 to Alice for dinner\n");

    ModelResponse response = genkit
        .generate(GenerateOptions.builder().model(model).prompt("Transfer $150 to Alice for dinner")
            .system("You are a banking assistant. Use the confirmTransfer tool for any transfers.")
            .tools(List.of(confirmTransferTool)).build());

    System.out.println("Response finish reason: " + response.getFinishReason());

    // Check if we got an interrupt
    if (response.isInterrupted()) {
      System.out.println("✓ Generation was interrupted!");
      System.out.println("  Number of interrupts: " + response.getInterrupts().size());

      Part interrupt = response.getInterrupts().get(0);
      Map<String, Object> metadata = interrupt.getMetadata();
      System.out.println("  Interrupt metadata: " + metadata);

      // Get user confirmation
      System.out.println("\n=== Step 2: Get User Confirmation ===\n");
      System.out.print("Confirm transfer of $150 to Alice? (yes/no): ");
      String userInput = scanner.nextLine().trim().toLowerCase();
      boolean confirmed = userInput.equals("yes") || userInput.equals("y");

      // Create the response to the interrupt
      ConfirmationOutput userResponse = new ConfirmationOutput(confirmed,
          confirmed ? "User approved" : "User declined");

      // Use the tool's respond helper
      Part responseData = confirmTool.respond(interrupt, userResponse);

      System.out.println("\n=== Step 3: Resume Generation ===\n");
      System.out.println("Resuming with user " + (confirmed ? "confirmation" : "rejection") + "...\n");

      // Resume generation with the user's response
      ModelResponse resumedResponse = genkit
          .generate(GenerateOptions.builder().model(model).messages(response.getMessages()) // Include
              // previous
              // context
              .tools(List.of(confirmTransferTool))
              .resume(ResumeOptions.builder().respond(responseData.getToolResponse()).build()).build());

      System.out.println("Final response: " + resumedResponse.getText());
      System.out.println("Finish reason: " + resumedResponse.getFinishReason());
    } else {
      System.out.println("Response (no interrupt): " + response.getText());
    }

    System.out.println("\n=== Generate Demo Complete ===");
  }

  /**
   * Demo using ExecutablePrompt with interrupts.
   * 
   * <p>
   * This shows how to use interrupts with the prompt() API, which allows you to
   * load and execute .prompt files with tool and interrupt support.
   */
  public void runPromptDemo() {
    System.out.println("╔════════════════════════════════════════════════════════════════╗");
    System.out.println("║    Interrupts with ExecutablePrompt - Prompt API Demo          ║");
    System.out.println("╚════════════════════════════════════════════════════════════════╝");
    System.out.println();
    System.out.println("This demo shows how to use interrupts with ExecutablePrompt.");
    System.out.println("It loads a .prompt file and adds tools with interrupt support.\n");

    // Load the prompt
    ExecutablePrompt<BankingInput> bankingPrompt = genkit.prompt("banking-assistant", BankingInput.class);

    // Create a simple confirm transfer interrupt tool
    @SuppressWarnings("unchecked")
    Tool<TransferRequest, ConfirmationOutput> confirmTool = (Tool<TransferRequest, ConfirmationOutput>) confirmTransferTool;

    // Initial request - transfer money
    System.out.println("=== Step 1: Execute Prompt with Tools ===\n");
    System.out.println("Using prompt: banking-assistant.prompt");
    System.out.println("Input: Transfer $200 to Bob for concert tickets\n");

    BankingInput input = new BankingInput("Transfer $200 to Bob for concert tickets");

    // Generate with tools - the prompt will use Genkit.generate() internally
    // which supports interrupts
    ModelResponse response = bankingPrompt.generate(input,
        GenerateOptions.builder().tools(List.of(confirmTransferTool)).build());

    System.out.println("Response finish reason: " + response.getFinishReason());

    // Check if we got an interrupt
    if (response.isInterrupted()) {
      System.out.println("✓ Prompt execution was interrupted!");
      System.out.println("  Number of interrupts: " + response.getInterrupts().size());

      Part interrupt = response.getInterrupts().get(0);
      Map<String, Object> metadata = interrupt.getMetadata();
      System.out.println("  Interrupt metadata: " + metadata);

      // Get user confirmation
      System.out.println("\n=== Step 2: Get User Confirmation ===\n");
      System.out.print("Confirm transfer of $200 to Bob? (yes/no): ");
      String userInput = scanner.nextLine().trim().toLowerCase();
      boolean confirmed = userInput.equals("yes") || userInput.equals("y");

      // Create the response to the interrupt
      ConfirmationOutput userResponse = new ConfirmationOutput(confirmed,
          confirmed ? "User approved" : "User declined");

      // Use the tool's respond helper
      Part responseData = confirmTool.respond(interrupt, userResponse);

      System.out.println("\n=== Step 3: Resume Prompt Execution ===\n");
      System.out.println("Resuming with user " + (confirmed ? "confirmation" : "rejection") + "...\n");

      // Resume generation with the user's response
      // Note: For full resume, you would use genkit.generate() with the messages
      ModelResponse resumedResponse = genkit.generate(GenerateOptions.builder().model(bankingPrompt.getModel())
          .messages(response.getMessages()).tools(List.of(confirmTransferTool))
          .resume(ResumeOptions.builder().respond(responseData.getToolResponse()).build()).build());

      System.out.println("Final response: " + resumedResponse.getText());
      System.out.println("Finish reason: " + resumedResponse.getFinishReason());
    } else {
      System.out.println("Response (no interrupt): " + response.getText());
    }

    System.out.println("\n=== Prompt Demo Complete ===");
  }

  public static void main(String[] args) {
    InterruptsApp app = new InterruptsApp();

    boolean demoMode = args.length > 0 && args[0].equals("--demo");
    boolean generateDemo = args.length > 0 && args[0].equals("--generate");
    boolean promptDemo = args.length > 0 && args[0].equals("--prompt");

    if (promptDemo) {
      app.runPromptDemo();
    } else if (generateDemo) {
      app.runGenerateDemo();
    } else if (demoMode) {
      app.runDemo();
    } else {
      app.runInteractive();
    }
  }
}

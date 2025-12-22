# Genkit Interrupts Sample

This sample demonstrates human-in-the-loop patterns using Genkit's interrupt mechanism, where AI operations can pause for user confirmation before executing sensitive actions.

## Features Demonstrated

- **Interrupt Pattern** - Pause execution for human confirmation
- **Sensitive Operations** - Money transfers requiring approval
- **Tool Interrupts** - Tools that request user input
- **Resume Flow** - Continue execution after user provides input
- **Session Persistence** - Maintain state across interrupts

## Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key

## Running the Sample

### Option 1: Direct Run

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/interrupts

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/interrupts

# Run with Genkit CLI
genkit start -- ./run.sh
```

## How Interrupts Work

```
┌─────────────────────────────────────────────────────────────┐
│  User: "Transfer $500 to John"                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  AI decides to use transferMoney tool                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Tool triggers INTERRUPT (sensitive operation)              │
│  ⏸️  Execution paused                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  User sees: "Confirm transfer of $500 to John? [y/n]"       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  User confirms: "y"                                         │
│  ▶️  Execution resumes with user confirmation                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Transfer executed successfully                             │
└─────────────────────────────────────────────────────────────┘
```

## Example Interaction

```
🏦 Welcome to AI Banking Assistant
Your current balance: $1000.00

You: Transfer $500 to Alice for rent

⚠️  CONFIRMATION REQUIRED
─────────────────────────────
Action: TRANSFER
Recipient: Alice
Amount: $500.00
Reason: rent

Do you approve this action? (yes/no): yes

✅ Transfer approved and executed!
New balance: $500.00

You: Transfer $2000 to Bob

⚠️  CONFIRMATION REQUIRED
─────────────────────────────
Action: TRANSFER
Recipient: Bob
Amount: $2000.00

Do you approve this action? (yes/no): no

❌ Transfer declined by user.
Your balance remains: $500.00
```

## Key Concepts

### InterruptConfig

Configure which operations should trigger interrupts:

```java
InterruptConfig interruptConfig = InterruptConfig.builder()
    .enabled(true)
    .tools(List.of("transferMoney", "deleteAccount"))
    .build();
```

### Creating an Interruptible Tool

```java
Tool<TransferRequest, TransferResult> transferTool = genkit.defineTool(
    "transferMoney",
    "Transfers money to another account",
    schema,
    TransferRequest.class,
    (ctx, request) -> {
        // This tool will trigger an interrupt
        ctx.interrupt(InterruptRequest.builder()
            .type("CONFIRMATION")
            .data(Map.of(
                "action", "TRANSFER",
                "recipient", request.getRecipient(),
                "amount", request.getAmount()
            ))
            .build());
        
        // Code here runs after user confirms
        return executeTransfer(request);
    });
```

### Handling Interrupts

```java
try {
    ModelResponse response = genkit.generate(options);
    // Normal response
} catch (InterruptException e) {
    InterruptRequest interrupt = e.getInterruptRequest();
    
    // Show confirmation to user
    boolean confirmed = promptUser(interrupt);
    
    if (confirmed) {
        // Resume with confirmation
        ModelResponse response = genkit.resume(
            ResumeOptions.builder()
                .interruptId(interrupt.getId())
                .response(new ConfirmationOutput(true, "User approved"))
                .build());
    }
}
```

## Account State

The sample simulates a bank account:

```java
public class AccountState {
    private double balance = 1000.00;
    private List<Transaction> transactions;
    
    public void transfer(String recipient, double amount) {
        if (amount > balance) {
            throw new InsufficientFundsException();
        }
        balance -= amount;
        transactions.add(new Transaction("TRANSFER", recipient, amount));
    }
}
```

## Use Cases for Interrupts

1. **Financial Transactions** - Require approval for transfers over a threshold
2. **Data Deletion** - Confirm before deleting important data
3. **External Actions** - Approve sending emails, making API calls
4. **Access Control** - Verify identity before sensitive operations
5. **Multi-Step Workflows** - Checkpoint approval in long processes

## Development UI

When running with `genkit start`, access the Dev UI at http://localhost:4000 to:

- Test interruptible flows
- View interrupt requests in traces
- Manually approve/reject interrupts
- Inspect state before and after interrupts

## See Also

- [Genkit Java README](../../README.md)
- [Chat Sessions Sample](../chat-session/README.md)
- [Multi-Agent Sample](../multi-agent/README.md)

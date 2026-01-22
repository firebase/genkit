## DeepSeek Sample

### How to Get Your DeepSeek API Key

A DeepSeek API key is a secret token for accessing DeepSeek's powerful AI models, obtained by signing up/logging in at platform.deepseek.com, navigating to the API Keys section in your dashboard, and clicking "Create API Key," requiring an account and potentially adding funds for usage beyond free limits.

**Steps:**
1. **Sign Up/Login**: Go to [platform.deepseek.com](https://platform.deepseek.com/) and log in (often with a Google account).
2. **Navigate to API Keys**: Find the "API Keys" section in your dashboard (usually on the left sidebar).
3. **Create Key**: Click the "Create API Key" button and give it a name (e.g., "my-app").
4. **Copy Key**: Copy the generated key immediately as it's shown only once.
5. **Add Credits (if needed)**: You might need to add funds or a payment method for usage beyond the free tier.

### Usage

1. Setup environment and install dependencies:
```bash
uv venv
source .venv/bin/activate

uv sync
```

2. Set DeepSeek API key (get one from [DeepSeek Platform](https://platform.deepseek.com/)):
```bash
export DEEPSEEK_API_KEY=your-api-key
```

3. Run the sample:
```bash
genkit start -- uv run src/main.py
```

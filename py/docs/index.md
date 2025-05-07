# What is Genkit

Genkit is a framework designed to help you build AI-powered applications and features.
It provides open source libraries for Python, Node.js and Go, plus developer tools for testing
and debugging.

This documentation covers Genkit for Python.
If you're a Go developer, see the [Genkit Go documentation](https://firebase.google.com/docs/genkit-go/get-started-go).
If you're a Node.js developer, see the [Genkit JS documentation](https://firebase.google.com/docs/genkit).

You can deploy and run Genkit libraries anywhere Python is supported. It's designed to work with
many AI model providers and vector databases. While we offer integrations for Firebase and Google Cloud,
you can use Genkit independently of any Google services.

[Get started](./get-started.md){ .md-button .md-button--primary }

## Key capabilities

<table class="responsive key-functions">
<tr>
  <td><strong>Unified API for AI generation</strong></td>
  <td>Use one API to generate or stream content from various AI models. Works with multimodal input/output and custom model settings.</td>
</tr>
<tr>
  <td><strong>Structured output</strong></td>
  <td>Generate or stream structured objects (like JSON) with built-in validation. Simplify integration with your app and convert unstructured data into a usable format.</td>
</tr>
<tr>
  <td><strong>Tool calling</strong></td>
  <td>Let AI models call your functions and APIs as tools to complete tasks. The model decides when and which tools to use.</td>
</tr>
<tr>
  <td><strong>Data retrieval</strong></td>
  <td>Improve the accuracy and relevance of generated output by integrating your data. Simple APIs help you embed, index, and retrieve information from various sources.</td>
</tr>
<tr>
  <td><strong>Prompt templating</strong></td>
  <td>(COMING SOON) Create effective prompts that include rich text templating, model settings, multimodal support, and tool integration - all within a compact, runnable prompt file.</td>
</tr>
<tr>
  <td><strong>Chat</strong></td>
  <td>(COMING SOON) Genkit offers a chat-specific API that facilitates multi-turn conversations with AI models, which can be stateful and persistent.</td>
</tr>
<tr>
  <td><strong>Agents</strong></td>
  <td>(COMING SOON) Create intelligent agents that use tools (including other agents) to help automate complex tasks and workflows.</td>
</tr>
</table>

See the following code samples for a concrete idea of how to use these capabilities in code:

=== "Basic generation"

    ```py
    import asyncio
    from genkit.ai import Genkit
    from genkit.plugins.google_genai import GoogleAI

    ai = Genkit(
        plugins=[GoogleAI()],
        model='googleai/gemini-2.0-flash',
    )

    async def main():
        result = await ai.generate(prompt=f'Why is AI awesome?')
        print(result.text)

        stream, _ = ai.generate_stream(prompt=f'Tell me a story')
        async for chunk in stream:
            print(chunk.text)

    ai.run_main(main())
    ```

=== "Structured output"

    ```py
    import asyncio
    import json
    from pydantic import BaseModel, Field
    from genkit.ai import Genkit
    from genkit.plugins.google_genai import GoogleAI

    ai = Genkit(
        plugins=[GoogleAI()],
        model='googleai/gemini-2.0-flash',
    )

    class RpgCharacter(BaseModel):
        """An RPG game character."""

        name: str = Field(description='name of the character')
        back_story: str = Field(description='back story')
        abilities: list[str] = Field(description='list of abilities (3-4)')

    async def main():
        result = await ai.generate(
            prompt=f'generate an RPG character named Glorb',
            output_schema=RpgCharacter,
        )
        print(json.dumps(result.output))

    ai.run_main(main())
    ```

=== "Tool calling"

    ```py
    import asyncio
    from pydantic import BaseModel, Field
    from genkit.ai import Genkit
    from genkit.plugins.google_genai import GoogleAI

    ai = Genkit(
        plugins=[GoogleAI()],
        model='googleai/gemini-2.0-flash',
    )

    class WeatherToolInput(BaseModel):
        location: str = Field(description='weather location')

    @ai.tool()
    def get_weather(input:WeatherToolInput) -> str:
        """Use it get the weather."""
        return f'Weather in {input.location} is 23°'

    async def main():
        result = await ai.generate(
            prompt='What is the weather in London?',
            tools=['get_weather']
        )
        print(result.text)

    ai.run_main(main())
    ```

## Development tools

Genkit provides a command-line interface (CLI) and a local Developer UI to make building AI applications easier. These tools help you:

- **Experiment:** Test and refine your AI functions, prompts, and queries.
- **Debug:** Find and fix issues with detailed execution traces.
- **Evaluate:** Assess generated results across multiple test cases.

## Connect with us

- **Join the community:** Stay updated, ask questions, and share your work on our [Discord server](https://discord.gg/qXt5zzQKpc).
- **Provide feedback:** Report issues or suggest new features using our GitHub [issue tracker](https://github.com/firebase/genkit/issues).

## Next steps

Learn how to build your first AI application with Genkit in our [Get started](./get-started.md) guide.

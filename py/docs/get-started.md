# Get Started

Get started with Genkit using Python (alpha)

The Genkit libraries for Python are now available for preview! Because the
Python libraries are currently in Alpha, you might see API and functional
changes as development progresses. We recommend using it only for prototyping
and exploration.

If you discover issues with the libraries or this documentation please report
them in our [GitHub repository](https://github.com/firebase/genkit/).

This guide shows you how to get started with Genkit in a Python app.

## Requirements

* Python 3.10 or later. See [Download and
  install](https://www.python.org/downloads/) in the official Python docs.

* Node.js 20 or later (for the Genkit CLI and UI). See the below for a brief
  guide on installing Node.

## Create and explore a sample project

1.  Create a new project directory:

    ```posix-terminal
    mkdir genkit-intro && cd genkit-intro
    ```

2.  (recommended) Create a Python virtual environment:

    ```bash
    python3 -m venv .
    ```

    (activate if necessary, depending on the environment)

    ```bash
    source bin/activate  # for bash
    ```

3.  Install dependencies

    ```bash
    pip3 install genkit
    pip3 install genkit-plugin-google-genai
    ```

    Or create a `requirements.txt` file

    ```
    genkit
    genkit-plugin-google-genai
    ```

    and run:

    ```bash
    pip3 install -r requirements.txt
    ```

4.  Configure your model API key

    The simplest way to get started is with Google AI Gemini API. Make sure it's
    [available in your region](https://ai.google.dev/available_regions).

    [Generate an API key](https://aistudio.google.com/app/apikey) for the
    Gemini API using Google AI Studio. Then, set the `GEMINI_API_KEY`
    environment variable to your key:

    ```posix-terminal
    export GEMINI_API_KEY=<your API key>
    ```

5.  Create `main.py` file:

    ```python
    import json
    from pydantic import BaseModel, Field
    from genkit.ai import Genkit
    from genkit.plugins.google_genai import GoogleAI

    ai = Genkit(
        plugins=[GoogleAI()],
        model='googleai/gemini-2.0-flash',
    )

    class RpgCharacter(BaseModel):
        name: str = Field(description='name of the character')
        back_story: str = Field(description='back story')
        abilities: list[str] = Field(description='list of abilities (3-4)')

    @ai.flow()
    async def generate_character(name: str):
        result = await ai.generate(
            prompt=f'generate an RPG character named {name}',
            output_schema=RpgCharacter,
        )
        return result.output

    async def main() -> None:
        print(json.dumps(await generate_character('Goblorb'), indent=2))

    ai.run_main(main())
    ```

6.  Run your app. Genkit apps are just regular python application. Run them
    however you normally run your app.

    ```bash
    python3 main.py
    ```

7.  Inspect your app with the Genkit Dev UI

    See instructions for installing the Genkit CLI (which includes the Dev UI)
    below.

    To inspect your app with Genkit Dev UI run with `genkit start -- <app>`
    command. E.g.:

    ```bash
    genkit start -- python3 main.py
    ```

    The command will print the Dev UI URL. E.g.:

    ```
    Genkit Developer UI: http://localhost:4000
    ```

## Install Genkit CLI

1.  If you don't already have Node 20 or newer on your system, install it now.

    Recommendation: The [`nvm`](https://github.com/nvm-sh/nvm) and
    [`nvm-windows`](https://github.com/coreybutler/nvm-windows) tools are a
    convenient way to install specific versions of Node if it's not already
    installed on your system. These tools install Node on a per-user basis, so
    you don't need to make system-wide changes.

    To install `nvm`:

    === "Linux, macOS, etc."

        Run the following command:

        ```posix-terminal
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
        ```

    === "Windows"

        Download and run the installer as described in the [nvm-windows
        docs](https://github.com/coreybutler/nvm-windows?tab=readme-ov-file#install-nvm-windows).

        Then, to install Node and `npm`, open a new shell and run the following
        command:

        ```posix-terminal
        nvm install 20
        ```

2.  Install the Genkit CLI by running the following command:

    ```posix-terminal
    npm i -g genkit-cli
    ```

    This command installs the Genkit CLI into your Node installation directory so
    that it can be used outside of a Node project.

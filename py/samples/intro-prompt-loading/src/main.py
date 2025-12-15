
import asyncio
from typing import Any
from genkit.core.registry import Registry
from genkit.blocks.prompt import load_prompt_folder
from genkit.aio import Genkit
from genkit.plugins.google_genai import google_genai

# Define user input schema
from pydantic import BaseModel

class UserInput(BaseModel):
    user: str

def main():
    registry = Registry()
    
    # Initialize plugins (e.g., Google GenAI for the model used in prompts)
    # Using a placeholder API key or assuming environment variable setup
    # Note: In a real scenario, plugins need proper configuration.
    
    ai = Genkit(plugins=[google_genai(api_key='TEST_KEY')], registry=registry)

    async def run_sample():
        # Load prompts from the 'prompts' directory
        # This will load:
        # - welcome.prompt as 'dotprompt/welcome'
        # - greetings/bye.prompt as 'dotprompt/greetings.bye'
        # - _footer.prompt as a partial named 'footer'
        await load_prompt_folder(registry, root='./prompts')

        # Lookup and run the welcome prompt
        welcome_prompt = registry.lookup_action_by_key('/prompt/dotprompt/welcome')
        if welcome_prompt:
            print(f"Running prompt: {welcome_prompt.name}")
            # Note: In a real run we would call execute/run, but here we just show it's loaded
            response = await welcome_prompt.arun_raw(
                {"user": "Developer"}
            )
            print("Response:", response.response)
        
        # Lookup and run the nested bye prompt
        bye_prompt = registry.lookup_action_by_key('/prompt/dotprompt/greetings.bye')
        if bye_prompt:
             print(f"Running prompt: {bye_prompt.name}")
             response = await bye_prompt.arun_raw(
                {"user": "Developer"}
            )
             print("Response:", response.response)

    asyncio.run(run_sample())

if __name__ == '__main__':
    main()

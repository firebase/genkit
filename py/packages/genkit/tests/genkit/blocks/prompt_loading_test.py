import pytest
from pathlib import Path
from genkit.core.registry import Registry
from genkit.blocks.prompt import load_prompt_file, load_prompt_folder

@pytest.mark.asyncio
async def test_load_prompt_file(tmp_path: Path):
    registry = Registry()
    prompt_file = tmp_path / 'hello.prompt'
    prompt_file.write_text(
        """---
model: googleai/gemini-2.5-flash
input:
  schema:
    username: string
---
Hello {{username}}!
"""
    )
    
    prompt = await load_prompt_file(registry, prompt_file, 'hello')
    assert prompt._variant is None
    assert prompt._model == 'googleai/gemini-2.5-flash'


@pytest.mark.asyncio
async def test_load_prompt_folder(tmp_path: Path):
    registry = Registry()
    
    # Create structure:
    # prompts/
    #   hello.prompt
    #   other/
    #     greeting.prompt
    #   _partial.prompt
    
    prompts_dir = tmp_path / 'prompts'
    prompts_dir.mkdir()
    
    (prompts_dir / 'hello.prompt').write_text(
        """---
model: googleai/gemini-2.5-flash
input:
  schema:
    username: string
---
Hello {{username}}!
"""
    )
    
    other_dir = prompts_dir / 'other'
    other_dir.mkdir()
    
    (other_dir / 'greeting.prompt').write_text(
        """---
model: googleai/gemini-2.5-flash
input:
  schema:
    name: string
---
Greetings {{name}} from nested!
"""
    )

    (prompts_dir / '_partial.prompt').write_text("PARTIAL CONTENT")

    await load_prompt_folder(registry, prompts_dir)
    
    # Verify hello prompt
    hello_action = registry.lookup_action_by_key('/prompt/dotprompt/hello')
    assert hello_action is not None
    
    # Verify nested prompt
    # sub/dir/my.prompt -> sub.dir.my
    # here: other/greeting.prompt -> other.greeting
    greeting_action = registry.lookup_action_by_key('/prompt/dotprompt/other.greeting')
    assert greeting_action is not None

@pytest.mark.asyncio
async def test_load_prompt_folder_custom_ns(tmp_path: Path):
    registry = Registry()
    prompts_dir = tmp_path / 'prompts'
    prompts_dir.mkdir()
    
    (prompts_dir / 'hello.prompt').write_text("Hello")
    
    await load_prompt_folder(registry, prompts_dir, ns='my_ns')
    
    hello_action = registry.lookup_action_by_key('/prompt/my_ns/hello')
    assert hello_action is not None


@pytest.mark.asyncio
async def test_load_prompt_variant(tmp_path: Path):
    registry = Registry()
    
    prompts_dir = tmp_path / 'prompts'
    prompts_dir.mkdir()
    
    # helper.prompt -> dotprompt/helper
    (prompts_dir / 'helper.prompt').write_text("Helper")
    
    # helper.chat.prompt -> dotprompt/helper.chat
    (prompts_dir / 'helper.chat.prompt').write_text("Helper Chat Variant")
    
    await load_prompt_folder(registry, prompts_dir)
    
    # Check base
    helper = registry.lookup_action_by_key('/prompt/dotprompt/helper')
    assert helper is not None
    
    # Check variant
    helper_variant = registry.lookup_action_by_key('/prompt/dotprompt/helper.chat')
    assert helper_variant is not None
    assert helper_variant.name == "dotprompt/helper.chat"

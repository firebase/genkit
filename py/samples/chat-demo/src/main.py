# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Chat Demo with Streamlit UI.

Key features demonstrated in this sample:

| Feature Description                     | Example Usage                           |
|-----------------------------------------|-----------------------------------------|
| ai.chat() convenience API               | `chat = ai.chat(system='...')`          |
| Chat.send() for messages                | `response = await chat.send('Hi')`      |
| Chat.send_stream() for streaming        | `result = chat.send_stream('Hi')`       |
| Thread-based conversations              | `ai.chat(thread='conv1')`               |
| Multiple parallel conversations         | Each conversation is a separate thread  |

This sample implements a web-based chatbot using Streamlit. It uses the
ai.chat() convenience API with threads for managing multiple conversations.
"""

import asyncio
import logging
import os

import streamlit as st
import structlog

from genkit.ai import Genkit
from genkit.blocks.model import GenerateResponseChunkWrapper, GenerateResponseWrapper, Message
from genkit.core.typing import Part, TextPart
from genkit.plugins.anthropic import Anthropic
from genkit.plugins.compat_oai import OpenAI
from genkit.plugins.deepseek import DeepSeek
from genkit.plugins.google_genai import GoogleAI, VertexAI
from genkit.plugins.ollama import Ollama
from genkit.plugins.vertex_ai import ModelGardenPlugin
from genkit.plugins.xai import XAI

logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger(__name__)

st.set_page_config(page_title='Genkit Chat Demo', page_icon='💬')
st.title('💬 Genkit Chat Demo')

# --- Model Definitions ---
DEFAULT_MODEL = 'googleai/gemini-3-flash-preview'

AVAILABLE_MODELS = {
    'Google (Gemini API)': [
        'googleai/gemini-3-flash-preview',
        'googleai/gemini-3-pro-preview',
        'googleai/gemini-2.5-pro',
        'googleai/gemini-2.0-flash',
        'googleai/gemini-2.0-pro-exp-02-05',
    ],
    'Vertex AI (Gemini)': [
        'vertexai/gemini-2.5-pro',
        'vertexai/gemini-2.5-flash',
        'vertexai/gemini-2.0-flash',
        'vertexai/gemini-2.0-flash-lite',
    ],
    'Anthropic': [
        'anthropic/claude-sonnet-4-5',
        'anthropic/claude-opus-4-5',
        'anthropic/claude-haiku-4-5',
        'anthropic/claude-3-5-sonnet',
    ],
    'DeepSeek': [
        'deepseek/deepseek-chat',
        'deepseek/deepseek-reasoner',
    ],
    'xAI': [
        'xai/grok-4',
        'xai/grok-3',
        'xai/grok-2-latest',
        'xai/grok-2-vision-1212',
        'xai/grok-2-1212',
        'xai/grok-beta',
    ],
    'OpenAI': [
        'openai/gpt-5.1',
        'openai/gpt-5',
        'openai/gpt-4o',
        'openai/gpt-4o-mini',
        'openai/o3',
        'openai/o1',
    ],
    'Vertex AI Model Garden': [
        'modelgarden/anthropic/claude-3-5-sonnet-v2@20241022',
        'modelgarden/anthropic/claude-3-opus@20240229',
        'modelgarden/anthropic/claude-3-sonnet@20240229',
        'modelgarden/anthropic/claude-3-haiku@20240307',
        'modelgarden/meta/llama-3.1-405b-instruct-maas',
        'modelgarden/meta/llama-3.2-90b-vision-instruct-maas',
    ],
    'Ollama': [],  # Dynamically populated
}

# Fetch Ollama models if provider selected or just list them if server is running
try:
    import ollama

    try:
        ollama_client = ollama.Client()
        models_resp = ollama_client.list()
        AVAILABLE_MODELS['Ollama'] = [f'ollama/{m.model}' for m in models_resp.models]
    except Exception:
        AVAILABLE_MODELS['Ollama'] = ['ollama/llama3.2', 'ollama/gemma2']
except ImportError:
    AVAILABLE_MODELS['Ollama'] = ['ollama/llama3.2', 'ollama/gemma2']

# Flatten available models list for default selection
all_models = [m for models in AVAILABLE_MODELS.values() for m in models]
default_idx = all_models.index(DEFAULT_MODEL) if DEFAULT_MODEL in all_models else 0

# --- State Initialization ---
if 'selected_provider' not in st.session_state:
    st.session_state['selected_provider'] = list(AVAILABLE_MODELS.keys())[0]
if 'selected_model' not in st.session_state:
    st.session_state['selected_model'] = AVAILABLE_MODELS[st.session_state['selected_provider']][0]


def update_provider() -> None:
    """Reset model when provider changes to avoids errors."""
    pass


# --- Sidebar Configuration ---
api_keys = {}
PROVIDERS = {
    'Google (Gemini API)': 'GEMINI_API_KEY',
    'Anthropic': 'ANTHROPIC_API_KEY',
    'DeepSeek': 'DEEPSEEK_API_KEY',
    'xAI': 'XAI_API_KEY',
    'OpenAI': 'OPENAI_API_KEY',
    'Vertex AI Project': 'VERTEX_AI_PROJECT_ID',
    'Vertex AI Location': 'VERTEX_AI_LOCATION',
}

with st.sidebar:
    # 1. Model Selection (Pinned to Top)
    st.header('Model Selection')
    provider = st.selectbox(
        'Provider',
        list(AVAILABLE_MODELS.keys()),
        key='selected_provider',
        on_change=update_provider,
    )

    curr_prov = st.session_state['selected_provider']
    # Ensure selected model is valid for provider
    valid_models = AVAILABLE_MODELS[curr_prov]
    if st.session_state['selected_model'] not in valid_models:
        st.session_state['selected_model'] = valid_models[0]

    st.selectbox(
        'Model',
        valid_models,
        key='selected_model',
    )
    st.caption(f'Selected: `{st.session_state["selected_model"]}`')

    enable_streaming = st.checkbox('Enable Streaming', value=True)
    st.divider()

    # 2. Authentication
    st.header('Authentication')
    for label, env_var in PROVIDERS.items():
        val = os.environ.get(env_var)
        if not val:
            try:
                val = st.secrets.get(env_var)
            except Exception:
                val = None

        if val:
            st.success(f'{label}: Configured', icon='✅')
            api_keys[env_var] = val
        else:
            user_key = st.text_input(f'{label} API Key', type='password', help=f'Set {env_var}')
            if user_key:
                os.environ[env_var] = user_key
                api_keys[env_var] = user_key
                st.rerun()
            else:
                st.warning(f'{label}: Not set', icon='⚠️')
                api_keys[env_var] = None
    st.divider()

# --- Main Logic ---

# Init Genkit with current state values
provider_val = st.session_state['selected_provider']
model_val = st.session_state['selected_model']

# Initialize plugins based on available keys
plugins = []
if api_keys.get('GEMINI_API_KEY'):
    plugins.append(GoogleAI())
if api_keys.get('ANTHROPIC_API_KEY'):
    plugins.append(Anthropic())
if api_keys.get('DEEPSEEK_API_KEY'):
    plugins.append(DeepSeek())
if api_keys.get('XAI_API_KEY'):
    plugins.append(XAI())
if api_keys.get('OPENAI_API_KEY'):
    plugins.append(OpenAI())

# Always add Ollama if it has models or just by default (no auth needed typically)
if provider_val == 'Ollama':
    plugins.append(Ollama())

if api_keys.get('VERTEX_AI_PROJECT_ID') and api_keys.get('VERTEX_AI_LOCATION'):
    # Add Model Garden Support
    plugins.append(
        ModelGardenPlugin(project_id=api_keys['VERTEX_AI_PROJECT_ID'], location=api_keys['VERTEX_AI_LOCATION'])
    )
    # Add Vertex AI Gemini Support
    plugins.append(VertexAI(project=api_keys['VERTEX_AI_PROJECT_ID'], location=api_keys['VERTEX_AI_LOCATION']))

if not plugins and provider_val != 'Ollama':
    st.error('No API keys provided for selected provider.')
    st.stop()

ai = Genkit(
    plugins=plugins,
    model=model_val,
)

# Initialize conversation threads
# We use a simple dict to track thread names and their display messages
if 'threads' not in st.session_state:
    st.session_state['threads'] = ['Conversation 1']
    st.session_state['active_thread'] = 'Conversation 1'
    st.session_state['thread_messages'] = {'Conversation 1': []}  # For UI display

# 3. Conversations (Sidebar - Appended)
with st.sidebar:
    st.header('Conversations')

    if st.button('➕ New Conversation', use_container_width=True):
        new_thread = f'Conversation {len(st.session_state["threads"]) + 1}'
        st.session_state['threads'].append(new_thread)
        st.session_state['thread_messages'][new_thread] = []
        st.session_state['active_thread'] = new_thread
        st.rerun()

    # Conversation List
    thread_names = st.session_state['threads']

    # Determine index dynamically to handle deletions or state changes safely
    try:
        idx = thread_names.index(st.session_state['active_thread'])
    except ValueError:
        idx = 0

    selected_thread = st.radio(
        'History',
        options=thread_names,
        index=idx,
        label_visibility='collapsed',
    )

    if selected_thread != st.session_state['active_thread']:
        st.session_state['active_thread'] = selected_thread
        st.rerun()

    if st.button('🗑️ Clear Current History', use_container_width=True):
        st.session_state['thread_messages'][st.session_state['active_thread']] = []
        st.rerun()


# Get the current thread name and messages for display
current_thread = st.session_state['active_thread']
messages = st.session_state['thread_messages'][current_thread]

# Display chat messages from history
for message in messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# Accept user input
if prompt := st.chat_input('What is up?'):
    # Add user message to chat history UI
    messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)

    # Generate response
    with st.chat_message('assistant'):
        message_placeholder = st.empty()
        full_response = ''

        async def run_chat() -> GenerateResponseWrapper:
            """Run chat using ai.chat() with thread support."""
            # Build message history from stored conversation (excluding the prompt we just added)
            history: list[Message] = []
            for msg_dict in messages[:-1]:  # Exclude last message (the prompt we just added)
                role = 'model' if msg_dict['role'] == 'assistant' else msg_dict['role']
                history.append(Message(role=role, content=[Part(root=TextPart(text=msg_dict['content']))]))

            # Create a chat with the history restored
            # Note: Using ChatOptions dict to pass messages (matches JS API)
            chat = ai.chat({'messages': history})

            # Streaming callback
            full_text = ''

            def on_chunk(chunk: GenerateResponseChunkWrapper) -> None:
                nonlocal full_text
                if hasattr(chunk, 'text') and chunk.text:
                    full_text += chunk.text
                    message_placeholder.markdown(full_text + '▌')

            # Send the message
            if enable_streaming:
                result = chat.send_stream(prompt)
                async for chunk in result.stream:
                    on_chunk(chunk)
                return await result.response
            else:
                return await chat.send(prompt)

        # Use asyncio.run which handles the loop correctly for this thread
        try:
            response = asyncio.run(run_chat())
            full_response = response.text
            message_placeholder.markdown(full_response)
            messages.append({'role': 'assistant', 'content': full_response})
        except Exception as e:
            # Check if it's a GenkitError or other exceptions and extract nice message
            error_msg = str(e)
            if hasattr(e, 'message'):
                error_msg = e.message
            elif hasattr(e, 'cause') and e.cause:
                error_msg = str(e.cause)

            st.error(f'Error: {error_msg}')
            # Stop spinner/execution
            st.stop()

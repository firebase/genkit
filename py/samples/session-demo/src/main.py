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

"""Session Demo."""

import asyncio
import logging
import os
from typing import Any

import streamlit as st
import structlog

from genkit.ai import Genkit
from genkit.blocks.model import GenerateResponseWrapper, Message
from genkit.core.typing import Part, TextPart
from genkit.plugins.anthropic import Anthropic
from genkit.plugins.compat_oai import OpenAI
from genkit.plugins.deepseek import DeepSeek
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.ollama import Ollama
from genkit.plugins.xai import XAI
from genkit.session import InMemorySessionStore, Session

logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger(__name__)

st.set_page_config(page_title='Genkit Session Demo', page_icon='📝', layout='wide')
st.title('📝 Genkit Session Demo')

# Check API keys
PROVIDERS = {
    'Google': 'GEMINI_API_KEY',
    'Anthropic': 'ANTHROPIC_API_KEY',
    'DeepSeek': 'DEEPSEEK_API_KEY',
    'xAI': 'XAI_API_KEY',
    'OpenAI': 'OPENAI_API_KEY',
}

api_keys = {}

with st.sidebar:
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

# --- Initialization ---

# Initialize simple session state variables if they don't exist
if 'step' not in st.session_state:
    st.session_state['step'] = 0
    st.session_state['session_data'] = None
    st.session_state['logs'] = []  # To show chat/logs

# Default model
DEFAULT_MODEL = 'googleai/gemini-3-flash-preview'

AVAILABLE_MODELS = {
    'Google': [
        'googleai/gemini-3-flash-preview',
        'googleai/gemini-3-pro-preview',
        'googleai/gemini-2.5-pro',
        'googleai/gemini-2.0-flash',
        'googleai/gemini-2.0-pro-exp-02-05',
    ],
    'Anthropic': [
        'anthropic/claude-sonnet-4-5',
        'anthropic/claude-opus-4-5',
        'anthropic/claude-haiku-4-5',
        'anthropic/claude-3-5-sonnet',
    ],
    'DeepSeek': [
        'deepseek/deepseek-v3',
        'deepseek/deepseek-r1',
        'deepseek/deepseek-chat',
        'deepseek/deepseek-reasoner',
    ],
    'xAI': [
        'xai/grok-4.1',
        'xai/grok-4',
        'xai/grok-3',
        'xai/grok-2-latest',
        'xai/grok-2-vision-1212',
        'xai/grok-2-1212',
        'xai/grok-beta',
    ],
    'OpenAI': [
        'openai/gpt-4.5-preview',
        'openai/gpt-4o',
        'openai/gpt-4o-mini',
        'openai/o1-preview',
        'openai/o1-mini',
        'openai/o3-mini',
    ],
    'Ollama': [],
}

# Fetch Ollama models
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

# Sidebar for configuration
with st.sidebar:
    st.header('Configuration')

    # Provider selection
    provider = st.selectbox('Provider', list(AVAILABLE_MODELS.keys()))

    # Model selection based on provider
    model_name = st.selectbox('Model', AVAILABLE_MODELS[provider], index=0)
    st.caption(f'Selected: `{model_name}`')

# Initialize Plugins
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
if provider == 'Ollama':
    plugins.append(Ollama())

if not plugins and provider != 'Ollama':
    st.error('No API keys provided for selected provider.')
    st.stop()

# Initialize Genkit (fresh per run)
ai = Genkit(
    plugins=plugins,
    model=model_name,
)

# Recover Session Object
session = None
if st.session_state['session_data']:
    # Use InMemoryStore with saved data to mimic persistence
    # In a real app, this would be a persistent store (Firestore, Redis)
    data = st.session_state['session_data']

    # Reconstruct messages with correct role mapping
    msgs = []
    for msg_dict in data['messages']:
        role = 'model' if msg_dict['role'] == 'assistant' else msg_dict['role']
        msgs.append(Message(role=role, content=[Part(root=TextPart(text=msg_dict['content']))]))

    # Update data (simplified InMemory structure)
    session_store_data: dict[str, Any] = {
        data['id']: {
            'id': data['id'],
            'state': data['state'],
            'messages': msgs,
            'created_at': None,
            'updated_at': None,
        }
    }

    store = InMemorySessionStore(data=session_store_data)

    async def load() -> Session | None:
        """Load session."""
        return await ai.load_session(data['id'], store=store)

    session = asyncio.run(load())

else:
    # No session active
    pass


def save_session(sess: Session) -> None:
    """Save session state to st.session_state."""
    msgs = []
    for m in sess.messages:
        # Extract text content (simplification)
        text = m.content[0].root.text if m.content and m.content[0].root.text else ''
        msgs.append({'role': m.role, 'content': text})

    st.session_state['session_data'] = {
        'id': sess.id,
        'state': sess.state,
        'messages': msgs,
    }


def add_log(role: str, text: str) -> None:
    """Add a log entry to the session state."""
    st.session_state['logs'].append({'role': role, 'text': text})


async def run_chat(sess: Session, prompt: str) -> GenerateResponseWrapper:
    """Run chat asynchronously."""
    return await sess.chat(prompt)


# --- Layout ---

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader('Interactive Session Flow')

    # Render logs
    for log in st.session_state['logs']:
        with st.chat_message(log['role']):
            st.markdown(log['text'])

    # Step Functions

    # Step 0: Start
    if st.session_state['step'] == 0:
        if st.button('Start Step 1: Create Session', type='primary'):
            sess = ai.create_session(initial_state={'user_name': 'Alice', 'preference': 'concise'})
            save_session(sess)
            add_log('system', "Session Created with initial state: `{'user_name': 'Alice', 'preference': 'concise'}`")
            st.session_state['step'] = 1
            st.rerun()

    # Step 1: Chat 1
    elif st.session_state['step'] == 1:
        if st.button('Run Step 1 Chat', type='primary'):
            prompt = "Hi, I'm Alice. What's my name and how many letters are in it?"
            add_log('user', prompt)

            with st.spinner('Generating...'):
                if session is None:
                    st.error('Session missing.')
                else:
                    resp = asyncio.run(run_chat(session, prompt))
                    save_session(session)
                    add_log('model', resp.text)

            st.session_state['step'] = 2
            st.rerun()

    # Step 2: Update State
    elif st.session_state['step'] == 2:
        st.info('Next: Update session state to change topic.')
        if st.button('Run Step 2: Update State (Math)', type='primary'):
            if session is None:
                st.error('Session missing.')
            else:
                session.update_state({'topic': 'math'})
                save_session(session)
                add_log('system', "State Updated: `{'topic': 'math'}`")
            st.session_state['step'] = 3
            st.rerun()

    # Step 3: Chat Math
    elif st.session_state['step'] == 3:
        if st.button('Run Step 3 Chat', type='primary'):
            prompt = 'Can you give me a simple problem related to my current topic?'
            add_log('user', prompt)

            with st.spinner('Generating...'):
                if session is None:
                    st.error('Session missing.')
                else:
                    resp = asyncio.run(run_chat(session, prompt))
                    save_session(session)
                    add_log('model', resp.text)

            st.session_state['step'] = 4
            st.rerun()

    # Step 4: Update State History
    elif st.session_state['step'] == 4:
        st.info('Next: Update session state to change topic again.')
        if st.button('Run Step 4: Update State (History)', type='primary'):
            if session is None:
                st.error('Session missing.')
            else:
                session.update_state({'topic': 'history'})
                save_session(session)
                add_log('system', "State Updated: `{'topic': 'history'}`")
            st.session_state['step'] = 5
            st.rerun()

    # Step 5: Chat History
    elif st.session_state['step'] == 5:
        if st.button('Run Step 5 Chat', type='primary'):
            prompt = 'Now tell me a fun fact about this new topic.'
            add_log('user', prompt)

            with st.spinner('Generating...'):
                if session is None:
                    st.error('Session missing.')
                else:
                    resp = asyncio.run(run_chat(session, prompt))
                    save_session(session)
                    add_log('model', resp.text)

            st.session_state['step'] = 6
            st.rerun()

    elif st.session_state['step'] == 6:
        st.success('Demo Complete!')
        if st.button('Restart Demo'):
            for key in ['step', 'session_data', 'logs']:
                del st.session_state[key]
            st.rerun()

with col2:
    st.subheader('Current Session State')
    if st.session_state['session_data']:
        st.json(st.session_state['session_data']['state'])
    else:
        st.info('No session active.')

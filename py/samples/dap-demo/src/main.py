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

"""Dynamic Action Provider (DAP) Demo.

This sample demonstrates how to use Dynamic Action Providers (DAPs) to provide
tools dynamically at runtime. DAPs are useful for integrating external tool
sources like MCP servers, plugin registries, or service meshes.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ DAP                 │ A "tool factory" that creates tools on-demand. │
    │                     │ Like a vending machine for AI tools.           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Dynamic Tool        │ A tool created at runtime, not at startup.     │
    │                     │ Like ordering custom pizza vs frozen.          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Cache               │ Remembers tools to avoid recreating them.      │
    │                     │ Like a notepad to avoid asking twice.          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ TTL (Time-To-Live)  │ How long cached tools stay fresh.              │
    │                     │ Like an expiration date on milk.               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Invalidation        │ Throwing away stale cached tools.              │
    │                     │ Like clearing your browser cache.              │
    └─────────────────────┴────────────────────────────────────────────────┘

Data Flow::

    User Request
         │
         ▼
    ┌─────────────────┐
    │     Flow        │  (e.g., weather_assistant)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐     ┌─────────────────┐
    │      DAP        │ ──► │   Tool Cache    │
    │  (weather-tools)│     │   (TTL: 5s)     │
    └────────┬────────┘     └─────────────────┘
             │
             │ Cache miss? Call provider function
             ▼
    ┌─────────────────┐
    │  Tool Provider  │  Creates dynamic tools
    │    Function     │  (get_weather, etc.)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Dynamic Tool   │  Used in AI generation
    │   Execution     │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │    Response     │
    └─────────────────┘

Running the Demo
----------------

1. Navigate to the sample directory::

    cd py/samples/dap-demo

2. Run with the sample runner::

    ../../bin/run_sample dap-demo

3. Or run directly with genkit start::

    uv run genkit start -- python src/main.py

Testing in the DevUI
--------------------

1. Open http://localhost:4000
2. Navigate to Flows
3. Select any flow (e.g., 'weather_assistant')
4. The default input values are pre-filled - just click Run

Available Flows
---------------

- **weather_assistant**: Get weather for a city using dynamic tools
- **finance_assistant**: Answer finance questions with multiple tools
- **multi_assistant**: Combine tools from multiple DAPs
- **refresh_tools_demo**: Demonstrate cache invalidation
- **list_dap_tools**: List all available tools from DAPs
"""

import asyncio
import random
from typing import Any

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit
from genkit.blocks.dap import DapCacheConfig, DapConfig, DapValue
from genkit.core.action import Action
from genkit.plugins.google_genai import GoogleAI

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

ai = Genkit(
    plugins=[GoogleAI()],
)


class WeatherInput(BaseModel):
    """Input for weather assistant flow."""

    city: str = Field(default='Tokyo', description='City name to get weather for')


class FinanceInput(BaseModel):
    """Input for finance assistant flow."""

    query: str = Field(default="What's the current price of AAPL stock?", description='Finance question to answer')


class MultiInput(BaseModel):
    """Input for multi-source assistant flow."""

    query: str = Field(
        default="What's the weather in London and how is the EUR/USD exchange rate?",
        description='Question that may require multiple tool sources',
    )


class RefreshInput(BaseModel):
    """Input for cache refresh demo flow."""

    source: str = Field(default='all', description="Which DAP to refresh: 'weather', 'finance', or 'all'")


class ListToolsInput(BaseModel):
    """Input for list tools flow."""

    source: str = Field(default='all', description="Which DAP to list: 'weather', 'finance', or 'all'")


class CurrencyConversion(BaseModel):
    """Input for currency conversion tool."""

    amount: float = Field(default=100.0, description='Amount to convert')
    from_currency: str = Field(default='USD', description='Source currency code')
    to_currency: str = Field(default='EUR', description='Target currency code')


async def fetch_weather_data(city: str) -> dict[str, Any]:
    """Simulate fetching weather from an external API."""
    await asyncio.sleep(0.1)  # Simulate network delay
    return {
        'city': city,
        'temperature': random.randint(15, 35),
        'conditions': random.choice(['Sunny', 'Cloudy', 'Rainy', 'Windy']),
        'humidity': random.randint(30, 80),
    }


async def fetch_stock_price(symbol: str) -> dict[str, Any]:
    """Simulate fetching stock price from an external API."""
    await asyncio.sleep(0.1)  # Simulate network delay
    return {
        'symbol': symbol.upper(),
        'price': round(random.uniform(50, 500), 2),
        'change': round(random.uniform(-5, 5), 2),
        'volume': random.randint(1000000, 10000000),
    }


async def weather_tools_provider() -> DapValue:
    """DAP function that provides weather-related tools.

    In a real scenario, this could connect to an MCP server, load tools from
    a plugin registry, or discover tools from a service mesh.

    Uses ai.dynamic_tool() to create unregistered tools that are returned
    directly to consumers without being in the global registry.
    """

    async def get_weather_impl(city: str) -> str:
        """Get current weather for a city."""
        data = await fetch_weather_data(city)
        return (
            f'Weather in {data["city"]}: {data["temperature"]}°C, {data["conditions"]}, Humidity: {data["humidity"]}%'
        )

    get_weather = ai.dynamic_tool(
        name='get_weather',
        fn=get_weather_impl,
        description='Get current weather for a city',
    )

    return {'tool': [get_weather]}


async def finance_tools_provider() -> DapValue:
    """DAP function that provides finance-related tools.

    This provider has a longer cache TTL because the available tools change
    less frequently than weather tools.
    """

    async def get_stock_price_impl(symbol: str) -> str:
        """Get current stock price by symbol."""
        data = await fetch_stock_price(symbol)
        change_str = f'+{data["change"]}' if data['change'] > 0 else str(data['change'])
        return f'{data["symbol"]}: ${data["price"]} ({change_str}%), Volume: {data["volume"]:,}'

    async def convert_currency_impl(input: CurrencyConversion) -> str:
        """Convert between currencies."""
        rates = {'USD': 1.0, 'EUR': 0.85, 'GBP': 0.73, 'JPY': 110.0}
        from_rate = rates.get(input.from_currency.upper(), 1.0)
        to_rate = rates.get(input.to_currency.upper(), 1.0)
        converted = input.amount / from_rate * to_rate
        return f'{input.amount} {input.from_currency.upper()} = {converted:.2f} {input.to_currency.upper()}'

    get_stock_price = ai.dynamic_tool(
        name='get_stock_price',
        fn=get_stock_price_impl,
        description='Get current stock price by symbol',
    )

    convert_currency = ai.dynamic_tool(
        name='convert_currency',
        fn=convert_currency_impl,
        description='Convert between currencies',
    )

    return {'tool': [get_stock_price, convert_currency]}


weather_dap = ai.define_dynamic_action_provider(
    config=DapConfig(
        name='weather-tools',
        description='Provides weather-related tools',
        cache_config=DapCacheConfig(ttl_millis=5000),
    ),
    fn=weather_tools_provider,
)

finance_dap = ai.define_dynamic_action_provider(
    config=DapConfig(
        name='finance-tools',
        description='Provides finance and market tools',
        cache_config=DapCacheConfig(ttl_millis=60000),
    ),
    fn=finance_tools_provider,
)


@ai.flow(description='Weather assistant using dynamically-provided tools')
async def weather_assistant(input: WeatherInput) -> str:
    """Get weather information for a city using dynamic tools.

    The weather tool is provided by the weather-tools DAP, which could be
    sourced from an MCP server, plugin registry, or other external system.
    """
    weather_tool = await weather_dap.get_action('tool', 'get_weather')

    if not weather_tool:
        return f'Weather service unavailable. Cannot get weather for {input.city}.'

    result = await weather_tool.arun(input.city)
    return str(result.response)


@ai.flow(description='Finance assistant using dynamically-provided tools')
async def finance_assistant(input: FinanceInput) -> str:
    """Answer finance questions using dynamic tools.

    The finance tools are provided by the finance-tools DAP with a longer
    cache TTL since the available tools change less frequently.
    """
    cache_result = await finance_dap._cache.get_or_fetch()  # noqa: SLF001 - accessing internal cache for demo
    tools = cache_result.get('tool', [])

    if not tools:
        return 'Finance service unavailable.'

    tool_names = [t.name for t in tools]
    return f'Available finance tools: {", ".join(tool_names)}. Query: {input.query}'


@ai.flow(description='Multi-source assistant combining tools from multiple DAPs')
async def multi_assistant(input: MultiInput) -> str:
    """Assistant that can use tools from multiple DAPs.

    This demonstrates how DAPs can be composed to provide tools from
    multiple sources (weather service + finance APIs) in a single query.
    """
    all_tools: list[Action[Any, Any]] = []

    weather_cache = await weather_dap._cache.get_or_fetch()  # noqa: SLF001
    all_tools.extend(weather_cache.get('tool', []))

    finance_cache = await finance_dap._cache.get_or_fetch()  # noqa: SLF001
    all_tools.extend(finance_cache.get('tool', []))

    if not all_tools:
        return 'No tools available.'

    tool_names = [t.name for t in all_tools]
    return f'Available tools from all sources: {", ".join(tool_names)}. Query: {input.query}'


@ai.flow(description='Demonstrate DAP cache invalidation')
async def refresh_tools_demo(input: RefreshInput) -> str:
    """Invalidate and refresh dynamic tools.

    In a real scenario, you might invalidate the cache when:
    - An MCP server restarts
    - A plugin is added/removed
    - Configuration changes
    """
    if input.source == 'weather':
        weather_dap.invalidate_cache()
        return 'Weather tools cache invalidated. Next request will fetch fresh tools.'
    elif input.source == 'finance':
        finance_dap.invalidate_cache()
        return 'Finance tools cache invalidated. Next request will fetch fresh tools.'
    elif input.source == 'all':
        weather_dap.invalidate_cache()
        finance_dap.invalidate_cache()
        return 'All DAP caches invalidated. Next requests will fetch fresh tools.'
    else:
        return f"Unknown source: {input.source}. Use 'weather', 'finance', or 'all'."


@ai.flow(description='List all tools available from DAPs')
async def list_dap_tools(input: ListToolsInput) -> str:
    """List all tools provided by a specific DAP or all DAPs.

    This demonstrates retrieving tools from DAP cache.
    """
    if input.source == 'weather':
        cache = await weather_dap._cache.get_or_fetch()  # noqa: SLF001
        tools = cache.get('tool', [])
        return f'Weather tools: {[t.name for t in tools]}'
    elif input.source == 'finance':
        cache = await finance_dap._cache.get_or_fetch()  # noqa: SLF001
        tools = cache.get('tool', [])
        return f'Finance tools: {[t.name for t in tools]}'
    elif input.source == 'all':
        weather_cache = await weather_dap._cache.get_or_fetch()  # noqa: SLF001
        finance_cache = await finance_dap._cache.get_or_fetch()  # noqa: SLF001
        weather_tools = weather_cache.get('tool', [])
        finance_tools = finance_cache.get('tool', [])
        all_names = [t.name for t in weather_tools] + [t.name for t in finance_tools]
        return f'All available tools: {all_names}'
    else:
        return f"Unknown source: {input.source}. Use 'weather', 'finance', or 'all'."


async def main() -> None:
    """Keep the server running for the DevUI.

    When running with 'genkit start', this keeps the process alive so flows
    can be tested through the DevUI at http://localhost:4000.
    """
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())

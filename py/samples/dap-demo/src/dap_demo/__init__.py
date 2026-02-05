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

What is DAP? (ELI5 - The Toy Box Analogy)
-----------------------------------------

Imagine you have two ways to get toys:

**Regular Tools (Static)** - Your Toy Box at Home::

    📦 Your Toy Box
    ├── 🚗 Car (always there)
    ├── 🧸 Teddy Bear (always there)
    └── 🎮 Game (always there)

You know exactly what toys you have. They're always in the same spot.
This is like regular ``@ai.tool()`` - defined once at startup, always available.

**DAP Tools (Dynamic)** - A Toy Rental Store::

    🏪 Toy Rental Store (DAP)
    ├── "What toys do you have today?"
    ├── Store checks inventory...
    └── "Today we have: 🚀 Rocket, 🦖 Dinosaur, 🎸 Guitar!"

The toys change! You ask the store, they check what's in stock RIGHT NOW,
and give you options. Tomorrow might be different toys!

Static vs Dynamic Tools::

    ┌─────────────────────────────────────────────────────────────────┐
    │                        WITHOUT DAP                               │
    │                                                                  │
    │   Your App Starts                                                │
    │        │                                                         │
    │        ▼                                                         │
    │   ┌─────────────┐                                                │
    │   │ Define tool │  @ai.tool("get_weather")                      │
    │   │ Define tool │  @ai.tool("get_stocks")                       │
    │   └─────────────┘                                                │
    │        │                                                         │
    │        ▼                                                         │
    │   Tools are FIXED. Can't add new ones without restarting.       │
    └─────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │                         WITH DAP                                 │
    │                                                                  │
    │   Your App Starts                                                │
    │        │                                                         │
    │        ▼                                                         │
    │   ┌───────────────────┐                                          │
    │   │ Register DAP      │  "Ask MCP server for tools"             │
    │   └───────────────────┘                                          │
    │        │                                                         │
    │        ▼                                                         │
    │   When you need tools...                                         │
    │        │                                                         │
    │        ▼                                                         │
    │   ┌───────────────────┐     ┌─────────────────────┐             │
    │   │ DAP asks server   │ ──► │ MCP Server says:    │             │
    │   │ "What tools now?" │     │ "I have 5 tools!"   │             │
    │   └───────────────────┘     └─────────────────────┘             │
    │        │                                                         │
    │        ▼                                                         │
    │   Tools could be DIFFERENT each time! 🎉                        │
    └─────────────────────────────────────────────────────────────────┘

Key Concepts::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ DAP                 │ A "tool factory" that creates tools on-demand. │
    │                     │ Like asking a store what's in stock.           │
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

Why Use DAP?
------------

1. **MCP Servers** - Connect to external tool servers that add/remove tools
2. **Plugin Systems** - Users can install new tools without restarting
3. **Multi-tenant** - Different users might have access to different tools
4. **Service Mesh** - Tools discovered from a network of microservices

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

    uv run genkit start -- python src/dap_demo/__init__.py

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

    This flow demonstrates using a model to answer queries with dynamic tools.
    """
    cache_result = await finance_dap._cache.get_or_fetch()  # noqa: SLF001 - accessing internal cache for demo
    tools = cache_result.get('tool', [])

    if not tools:
        return 'Finance service unavailable.'

    # Use a model to answer the query using the dynamic tools
    # Note: Dynamic tools are not in the global registry, so we invoke them directly.
    # For stock queries, use the get_stock_price tool
    get_stock_price = next((t for t in tools if t.name == 'get_stock_price'), None)
    if get_stock_price and 'stock' in input.query.lower():
        # Extract stock symbol from query (simple heuristic)
        words = input.query.upper().split()
        symbol = next((w for w in words if len(w) <= 5 and w.isalpha()), 'AAPL')
        result = await get_stock_price.arun(symbol)
        return str(result.response)

    # For currency queries, use the convert_currency tool
    convert_currency = next((t for t in tools if t.name == 'convert_currency'), None)
    if convert_currency and any(word in input.query.lower() for word in ['convert', 'exchange', 'currency']):
        result = await convert_currency.arun(CurrencyConversion())
        return str(result.response)

    tool_names = [t.name for t in tools]
    return f'Available finance tools: {", ".join(tool_names)}. Try asking about stocks or currency conversion.'


@ai.flow(description='Multi-source assistant combining tools from multiple DAPs')
async def multi_assistant(input: MultiInput) -> str:
    """Assistant that can use tools from multiple DAPs.

    This demonstrates how DAPs can be composed to provide tools from
    multiple sources (weather service + finance APIs) in a single query.

    Uses asyncio.gather for concurrent fetching.
    """
    all_tools: list[Action[Any, Any]] = []

    # Fetch from both DAPs concurrently for efficiency
    weather_cache, finance_cache = await asyncio.gather(
        weather_dap._cache.get_or_fetch(),  # noqa: SLF001
        finance_dap._cache.get_or_fetch(),  # noqa: SLF001
    )
    all_tools.extend(weather_cache.get('tool', []))
    all_tools.extend(finance_cache.get('tool', []))

    if not all_tools:
        return 'No tools available.'

    # Demonstrate composing tools from multiple sources
    # Collect results from all matching tools
    results: list[str] = []

    # For weather queries, use the weather tool
    get_weather = next((t for t in all_tools if t.name == 'get_weather'), None)
    if get_weather and 'weather' in input.query.lower():
        # Extract city name (simple heuristic - use first capitalized word after 'in')
        import re

        match = re.search(r'\bin\s+(\w+)', input.query, re.IGNORECASE)
        city = match.group(1) if match else 'London'
        result = await get_weather.arun(city)
        results.append(str(result.response))

    # For currency/exchange queries, use convert_currency tool
    convert_currency = next((t for t in all_tools if t.name == 'convert_currency'), None)
    if convert_currency and any(word in input.query.lower() for word in ['eur', 'usd', 'exchange', 'currency', 'rate']):
        result = await convert_currency.arun(CurrencyConversion(from_currency='EUR', to_currency='USD'))
        results.append(str(result.response))

    # For stock queries, use get_stock_price tool
    get_stock_price = next((t for t in all_tools if t.name == 'get_stock_price'), None)
    if get_stock_price and any(word in input.query.lower() for word in ['stock', 'price', 'aapl']):
        result = await get_stock_price.arun('AAPL')
        results.append(str(result.response))

    if results:
        return ' | '.join(results)

    tool_names = [t.name for t in all_tools]
    return f'Available tools: {", ".join(tool_names)}. Try asking about weather, stocks, or currency.'


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
        # Fetch from both DAPs concurrently for efficiency
        weather_cache, finance_cache = await asyncio.gather(
            weather_dap._cache.get_or_fetch(),  # noqa: SLF001
            finance_dap._cache.get_or_fetch(),  # noqa: SLF001
        )
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

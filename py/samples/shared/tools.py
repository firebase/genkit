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
"""Common tools for samples."""

import operator
import random

from .types import (
    CalculatorInput,
    CurrencyExchangeInput,
    WeatherInput,
)


def calculate(input: CalculatorInput) -> dict:
    """Perform basic arithmetic operations.

    Uses a dispatch table lookup and handles arithmetic edge cases.
    """
    operations = {
        'add': operator.add,
        'subtract': operator.sub,
        'multiply': operator.mul,
        'divide': operator.truediv,
    }

    op_name = input.operation.lower()
    handler = operations.get(op_name)

    if not handler:
        return {'error': f'Unknown operation: {op_name}'}

    try:
        a, b = float(input.a), float(input.b)
        result = handler(a, b)
    except ZeroDivisionError:
        return {'error': 'Division by zero'}
    except (ValueError, TypeError) as e:
        return {'error': f'Invalid numeric input: {e}'}

    return {
        'operation': op_name,
        'a': a,
        'b': b,
        'result': result,
    }


def convert_currency(input: CurrencyExchangeInput) -> str:
    """Convert currency amount.

    Args:
        input: Currency conversion parameters.

    Returns:
        Converted amount.
    """
    # Mock conversion rates
    rates = {
        ('USD', 'EUR'): 0.85,
        ('EUR', 'USD'): 1.18,
        ('USD', 'GBP'): 0.73,
        ('GBP', 'USD'): 1.37,
    }
    rate = rates.get((input.from_currency, input.to_currency), 1.0)
    converted = input.amount * rate
    return f'{input.amount} {input.from_currency} = {converted:.2f} {input.to_currency}'


def get_weather(input: WeatherInput) -> str:
    """Return a random realistic weather string for a city name.

    Args:
        input: Weather input location.

    Returns:
        Weather information with temperature in degree Celsius.
    """
    weather_options = [
        '32° C sunny',
        '17° C cloudy',
        '22° C cloudy',
        '19° C humid',
    ]
    return random.choice(weather_options)

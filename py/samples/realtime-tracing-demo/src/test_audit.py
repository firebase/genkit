#!/usr/bin/env python3
"""Audit test: Does realtime tracing actually work?

This test verifies whether the realtime tracing implementation
actually sends spans to the Dev UI as they START (not just end).
"""

import asyncio
import time

from genkit.ai import Genkit

ai = Genkit()


@ai.flow()
async def slow_flow(duration: int = 5) -> str:
    """A slow flow to test if spans appear BEFORE completion."""
    print(f'[FLOW START] slow_flow starting, will take {duration}s...')
    await asyncio.sleep(duration)
    print(f'[FLOW END] slow_flow completed')
    return f'Completed after {duration} seconds'


@ai.flow()
async def nested_flow() -> str:
    """A flow that calls other flows to test nested span visibility."""
    print('[FLOW START] nested_flow starting...')

    # Step 1
    print('[STEP 1] Starting first operation...')
    await asyncio.sleep(2)
    print('[STEP 1] Done')

    # Step 2 - call another flow
    print('[STEP 2] Calling slow_flow...')
    result = await slow_flow(3)
    print(f'[STEP 2] slow_flow returned: {result}')

    # Step 3
    print('[STEP 3] Final operation...')
    await asyncio.sleep(1)
    print('[STEP 3] Done')

    print('[FLOW END] nested_flow completed')
    return 'All done!'


async def main():
    print('=' * 60)
    print('REALTIME TRACING AUDIT TEST')
    print('=' * 60)
    print()
    print('If realtime tracing works correctly:')
    print('  - Open Dev UI at http://localhost:4000')
    print("  - Click on 'nested_flow' in the flows list")
    print('  - Run it')
    print('  - You should see the trace drawer open IMMEDIATELY')
    print('  - Spans should appear AS THEY START, not after completion')
    print()
    print('If realtime tracing is broken:')
    print("  - The trace drawer won't open until the flow completes")
    print("  - You'll only see spans AFTER the ~6 second flow finishes")
    print()
    print('=' * 60)
    print()

    # Keep alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())

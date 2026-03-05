"""
Bifrost 2.0 — Rate limiter pro Playwright requesty
"""
import asyncio
import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, default_delay: float = 3.0):
        self.default_delay = default_delay
        self.last_request: dict[str, float] = defaultdict(float)
        self.custom_delays: dict[str, float] = {}

    def set_delay(self, model_name: str, delay: float):
        self.custom_delays[model_name] = delay

    async def wait(self, model_name: str):
        delay = self.custom_delays.get(model_name, self.default_delay)
        elapsed = time.time() - self.last_request[model_name]
        if elapsed < delay:
            wait_time = delay - elapsed
            await asyncio.sleep(wait_time)
        self.last_request[model_name] = time.time()

    async def backoff(self, model_name: str, attempt: int):
        """Exponenciální backoff při chybách."""
        wait_time = min(self.default_delay * (2 ** attempt), 60)
        await asyncio.sleep(wait_time)
